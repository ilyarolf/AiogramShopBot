from bip_utils import Bip44Changes, Bip44Coins, Bip44, Bip39SeedGenerator, Bip84, Bip84Coins, Bip39MnemonicGenerator, \
    Bip39WordsNum, Base58Encoder


class CryptoAddressGenerator:
    def __init__(self, seed_str: str = None):
        if seed_str is not None:
            self.mnemonic_str = seed_str
            self.seed_bytes = Bip39SeedGenerator(self.mnemonic_str).Generate()
        else:
            mnemonic_gen = Bip39MnemonicGenerator().FromWordsNumber(Bip39WordsNum.WORDS_NUM_12)
            self.mnemonic_str = mnemonic_gen.ToStr()
            self.seed_bytes = Bip39SeedGenerator(self.mnemonic_str).Generate()

    def __generate_btc_pair(self) -> tuple:
        bip84_mst_ctx = Bip84.FromSeed(self.seed_bytes, Bip84Coins.BITCOIN)
        bip84_acc_ctx = bip84_mst_ctx.Purpose().Coin().Account(0)
        bip84_chg_ctx = bip84_acc_ctx.Change(Bip44Changes.CHAIN_EXT)
        bip84_addr_ctx = bip84_chg_ctx.AddressIndex(0).PublicKey().ToAddress()
        return bip84_addr_ctx, bip84_chg_ctx.AddressIndex(0).PrivateKey().ToWif()

    def __generate_ltc_pair(self) -> tuple:
        bip84_mst_ctx = Bip84.FromSeed(self.seed_bytes, Bip84Coins.LITECOIN)
        bip84_acc_ctx = bip84_mst_ctx.Purpose().Coin().Account(0)
        bip84_chg_ctx = bip84_acc_ctx.Change(Bip44Changes.CHAIN_EXT)
        bip84_addr_ctx = bip84_chg_ctx.AddressIndex(0).PublicKey().ToAddress()
        return bip84_addr_ctx, bip84_chg_ctx.AddressIndex(0).PrivateKey().ToWif()

    def __generate_trx_pair(self) -> tuple:
        bip44_mst_ctx = Bip44.FromSeed(self.seed_bytes, Bip44Coins.TRON)
        bip44_acc_ctx = bip44_mst_ctx.Purpose().Coin().Account(0)
        bip44_chg_ctx = bip44_acc_ctx.Change(Bip44Changes.CHAIN_EXT)
        bip44_addr_ctx = bip44_chg_ctx.AddressIndex(0).PublicKey().ToAddress()
        return bip44_addr_ctx, bip44_chg_ctx.AddressIndex(0).PrivateKey().ToWif()

    def __generate_eth_pair(self) -> tuple:
        bip44_mst_ctx = Bip44.FromSeed(self.seed_bytes, Bip44Coins.ETHEREUM)
        bip44_acc_ctx = bip44_mst_ctx.Purpose().Coin().Account(0)
        bip44_chg_ctx = bip44_acc_ctx.Change(Bip44Changes.CHAIN_EXT)
        bip44_addr_ctx = bip44_chg_ctx.AddressIndex(0).PublicKey().ToAddress()
        return bip44_addr_ctx, bip44_chg_ctx.AddressIndex(0).PrivateKey().ToWif()

    def __generate_sol_pair(self) -> tuple:
        bip44_def_ctx = Bip44.FromSeed(self.seed_bytes, Bip44Coins.SOLANA)
        bip44_acc_ctx = bip44_def_ctx.Purpose().Coin().Account(0)
        bip44_chg_ctx = bip44_acc_ctx.Change(Bip44Changes.CHAIN_EXT)
        bip44_addr_ctx = bip44_chg_ctx.PublicKey().ToAddress()
        pub_key = bip44_chg_ctx.PublicKey().RawCompressed().ToBytes()[1:]
        priv_key = bip44_chg_ctx.PrivateKey().Raw().ToBytes()
        phantom_wallet_private_key = Base58Encoder.Encode(priv_key + pub_key)
        return bip44_addr_ctx, phantom_wallet_private_key

    def get_private_keys(self) -> dict:
        return {'btc': self.__generate_btc_pair()[1],
                'ltc': self.__generate_ltc_pair()[1],
                'trx': self.__generate_trx_pair()[1],
                'eth': self.__generate_eth_pair()[1],
                'sol': self.__generate_sol_pair()[1]}

    def get_addresses(self):
        return {'btc': self.__generate_btc_pair()[0],
                'ltc': self.__generate_ltc_pair()[0],
                'trx': self.__generate_trx_pair()[0],
                'eth': self.__generate_eth_pair()[0],
                'sol': self.__generate_sol_pair()[0]}
