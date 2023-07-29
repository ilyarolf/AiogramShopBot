from bip_utils import Bip44Changes, Bip44Coins, Bip44, Bip39SeedGenerator, Bip84, Bip84Coins
from os import getenv

class CryptoAddressGenerator:
    def __init__(self,
                 seed: str = 'cloud broom leaf moment apple advance vocal fence envelope word arm ten hen struggle giant'):
        self.seed_bytes = Bip39SeedGenerator(seed).Generate()

    def __generate_btc_pair(self, i: int):
        bip84_mst_ctx = Bip84.FromSeed(self.seed_bytes, Bip84Coins.BITCOIN)
        bip84_acc_ctx = bip84_mst_ctx.Purpose().Coin().Account(0)
        bip84_chg_ctx = bip84_acc_ctx.Change(Bip44Changes.CHAIN_EXT)
        bip84_addr_ctx = bip84_chg_ctx.AddressIndex(i).PublicKey().ToAddress()
        private_key = bip84_chg_ctx.AddressIndex(i).PrivateKey().ToWif()
        return {"address": bip84_addr_ctx, "private_key": private_key}

    def __generate_ltc_pair(self, i: int):
        bip44_mst_ctx = Bip44.FromSeed(self.seed_bytes, Bip44Coins.LITECOIN)
        bip44_acc_ctx = bip44_mst_ctx.Purpose().Coin().Account(0)
        bip44_chg_ctx = bip44_acc_ctx.Change(Bip44Changes.CHAIN_EXT)
        bip44_addr_ctx = bip44_chg_ctx.AddressIndex(i).PublicKey().ToAddress()
        private_key = bip44_chg_ctx.AddressIndex(i).PrivateKey().ToWif()
        return {"address": bip44_addr_ctx, "private_key": private_key}

    def __generate_trx_pair(self, i: int):
        bip44_mst_ctx = Bip44.FromSeed(self.seed_bytes, Bip44Coins.TRON)
        bip44_acc_ctx = bip44_mst_ctx.Purpose().Coin().Account(0)
        bip44_chg_ctx = bip44_acc_ctx.Change(Bip44Changes.CHAIN_EXT)
        bip44_addr_ctx = bip44_chg_ctx.AddressIndex(i).PublicKey().ToAddress()
        private_key = bip44_chg_ctx.AddressIndex(i).PrivateKey().Raw()
        return {"address": bip44_addr_ctx, "private_key": private_key}

    def get_addresses(self, i):
        additive_number = getenv("ADDITIVE")
        if additive_number is not None:
            i = i + int(additive_number)
        return {'btc': self.__generate_btc_pair(i)['address'],
                'ltc': self.__generate_ltc_pair(i)['address'],
                'trx': self.__generate_trx_pair(i)['address']}

    def get_private_keys(self, i):
        additive_number = getenv("ADDITIVE")
        if additive_number is not None:
            i = i + int(additive_number)
        return {'btc': self.__generate_btc_pair(i)['private_key'],
                'ltc': self.__generate_ltc_pair(i)['private_key'],
                'trx': self.__generate_trx_pair(i)['private_key']}


if __name__ == "__main__":
    print(CryptoAddressGenerator().get_addresses(0))