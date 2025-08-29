from tsrkit_types import structure, Uint, Dictionary, Bytes

from jam.types.protocol.core import Gas, ServiceId
from jam.types.protocol.crypto import OpaqueHash, Hash
from jam.types.state.delta import AccountPreimages, AccountStorage as AS, Delta, AccountData as AD, AccountPreimages, \
	AccountMetadata, AccountLookup

@structure
class Service:
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

class AccountStorage(Dictionary[Bytes, Bytes, "key", "value"]):
	"""Storage dictionary"""
	...

@structure
class AccountData:
		service: Service
		preimages: AccountPreimages
		storage: AccountStorage

class InputAccounts(Dictionary[ServiceId, AccountData, "id", "data"]):
	def to_delta(self) -> Delta:
		delta = Delta({})
		for key, val in self.items():
			delta[key] = AD(
				service=AccountMetadata(
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
				storage=AS({Bytes(ServiceId(key).encode() + bytes(_key)): value for _key, value in val.storage.items()}),
				preimages=val.preimages,
				lookup=AccountLookup({})
			)
		return delta


class Stats(Dictionary[ServiceId,tuple[Gas,Uint[32]]]):
	...
