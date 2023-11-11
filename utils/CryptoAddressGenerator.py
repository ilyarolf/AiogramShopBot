from bip_utils import Bip44Changes, Bip44Coins, Bip44, Bip39SeedGenerator, Bip84, Bip84Coins, Bip39MnemonicGenerator, \
    Bip39WordsNum


class CryptoAddressGenerator:
    def __init__(self):
        mnemonic_gen = Bip39MnemonicGenerator().FromWordsNumber(Bip39WordsNum.WORDS_NUM_12)
        self.mnemonic_str = mnemonic_gen.ToStr()
        self.seed_bytes = Bip39SeedGenerator(self.mnemonic_str).Generate()

    def __generate_btc_pair(self, i: int) -> str:
        bip84_mst_ctx = Bip84.FromSeed(self.seed_bytes, Bip84Coins.BITCOIN)
        bip84_acc_ctx = bip84_mst_ctx.Purpose().Coin().Account(0)
        bip84_chg_ctx = bip84_acc_ctx.Change(Bip44Changes.CHAIN_EXT)
        bip84_addr_ctx = bip84_chg_ctx.AddressIndex(i).PublicKey().ToAddress()
        return bip84_addr_ctx

    def __generate_ltc_pair(self, i: int) -> str:
        bip84_mst_ctx = Bip84.FromSeed(self.seed_bytes, Bip84Coins.LITECOIN)
        bip84_acc_ctx = bip84_mst_ctx.Purpose().Coin().Account(0)
        bip84_chg_ctx = bip84_acc_ctx.Change(Bip44Changes.CHAIN_EXT)
        bip84_addr_ctx = bip84_chg_ctx.AddressIndex(i).PublicKey().ToAddress()
        return bip84_addr_ctx

    def __generate_trx_pair(self, i: int) -> str:
        bip44_mst_ctx = Bip44.FromSeed(self.seed_bytes, Bip44Coins.TRON)
        bip44_acc_ctx = bip44_mst_ctx.Purpose().Coin().Account(0)
        bip44_chg_ctx = bip44_acc_ctx.Change(Bip44Changes.CHAIN_EXT)
        bip44_addr_ctx = bip44_chg_ctx.AddressIndex(i).PublicKey().ToAddress()
        return bip44_addr_ctx

    def get_addresses(self, i):
        return {'btc': self.__generate_btc_pair(i),
                'ltc': self.__generate_ltc_pair(i),
                'trx': self.__generate_trx_pair(i)}
