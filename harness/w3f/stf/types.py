from dataclasses import dataclass

from jam.types.base import U64, U32, Dictionary, decodable_dictionary, Bytes
from jam.types.protocol.core import Gas, ServiceId
from jam.types.protocol.crypto import OpaqueHash, Hash
from jam.types.state.delta import PreImageLookup, AccountStorage as AS, Delta, AccountData as AD, LookupTimestamps
from jam.utils.codec import Codable
from jam.utils.codec.decorators import decodable_dataclass
from jam.utils.json import JsonSerde

@decodable_dataclass
@dataclass
class Service(Codable,JsonSerde):
    code_hash: OpaqueHash
    balance: U64
    min_item_gas: Gas
    min_memo_gas: Gas
    bytes: U64
    items: U32

@decodable_dictionary(Bytes, Bytes, key_name="key", value_name="value")
class AccountStorage(Dictionary[Bytes, Bytes]):
    """Storage dictionary"""
    ...


@decodable_dataclass
@dataclass
class AccountData(Codable, JsonSerde):
		service: Service
		preimages: PreImageLookup
		storage: AccountStorage

@decodable_dictionary(ServiceId, AccountData, key_name="id", value_name="data")
class InputAccounts(Dictionary):
		def to_delta(self) -> Delta:
				delta = Delta({})
				for key, val in self.items():
						delta[key] = AD(
								code_hash=val.service.code_hash,
								balance=val.service.balance,
								gas_limit=val.service.min_item_gas,
								min_gas=val.service.min_memo_gas,
								storage=AS({Hash.blake2b(key): value for key, value in val.storage.items()}),
								lookup=val.preimages,
								timestamps=LookupTimestamps({})
						)
				return delta