from tsrkit_types import structure, Uint, Dictionary, TypedBoundedVector

from jam.types.protocol.core import Gas, ServiceId
from jam.types.protocol.crypto import OpaqueHash
from jam.types.state.delta import AccountStorage, Delta, AccountData as AD, AccountPreimages, \
	AccountMetadata, AccountLookup


@structure
class Service:
	version: Uint[8]
	code_hash: OpaqueHash
	balance: Uint[64]
	min_item_gas: Gas
	min_memo_gas: Gas
	bytes: Uint[64]
	deposit_offset: Uint[64]
	items: Uint[32]
	creation_slot: Uint[32]
	last_accumulation_slot: Uint[32]
	parent_service: Uint[32]

Timestamps = TypedBoundedVector[Uint[32], 0, 3]


@structure
class AccountData:
		service: Service
		storage: AccountStorage
		preimage_blobs: AccountPreimages
		preimage_requests: AccountLookup

class InputAccounts(Dictionary[ServiceId, AccountData, "id", "data"]):
	def to_delta(self) -> Delta:
		delta = Delta({})
		for key, val in self.items():
			delta[key] = AD(
				service=AccountMetadata(
					version=val.service.version,
					code_hash=val.service.code_hash,
					balance=val.service.balance,
					gas_limit=val.service.min_item_gas,
					min_gas=val.service.min_memo_gas,
					num_o=val.service.bytes,
					num_i=val.service.items,
					gratis_offset=val.service.deposit_offset,
					created_at=val.service.creation_slot,
					accumulated_at=val.service.last_accumulation_slot,
					parent_service=val.service.parent_service
				),
				storage=val.storage,
				preimages=val.preimage_blobs,
				lookup=val.preimage_requests
			)
		return delta


class Stats(Dictionary[ServiceId,tuple[Gas,Uint[32]]]):
	...
