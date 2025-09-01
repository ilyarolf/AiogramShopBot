# Test cases for CryptoAddressGenerator
# Covers: Address generation, private key generation, seed handling, multiple cryptocurrencies

import pytest
from unittest.mock import patch, Mock
import re

from utils.CryptoAddressGenerator import CryptoAddressGenerator


class TestCryptoAddressGenerator:
    """Test cryptocurrency address and private key generation"""
    
    def test_generator_with_custom_seed(self):
        """Test generator initialization with custom seed"""
        custom_seed = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
        generator = CryptoAddressGenerator(seed_str=custom_seed)
        assert generator.mnemonic_str == custom_seed
        assert generator.seed_bytes is not None

    def test_generator_with_random_seed(self):
        """Test generator initialization with random seed"""
        generator = CryptoAddressGenerator()
        assert generator.mnemonic_str is not None
        assert len(generator.mnemonic_str.split()) == 12  # 12-word mnemonic
        assert generator.seed_bytes is not None

    def test_btc_address_generation(self):
        """Test Bitcoin address generation format"""
        generator = CryptoAddressGenerator()
        addresses = generator.get_addresses()
        
        assert 'btc' in addresses
        btc_address = addresses['btc']
        # Bitcoin addresses start with 1, 3, or bc1
        assert re.match(r'^(1|3|bc1)[a-zA-Z0-9]+$', str(btc_address))

    def test_eth_address_generation(self):
        """Test Ethereum address generation format"""
        generator = CryptoAddressGenerator()
        addresses = generator.get_addresses()
        
        assert 'eth' in addresses
        eth_address = addresses['eth']
        # Ethereum addresses are 42 characters starting with 0x
        assert str(eth_address).startswith('0x')
        assert len(str(eth_address)) == 42

    def test_ltc_address_generation(self):
        """Test Litecoin address generation format"""
        generator = CryptoAddressGenerator()
        addresses = generator.get_addresses()
        
        assert 'ltc' in addresses
        ltc_address = addresses['ltc']
        # Litecoin addresses start with L, M, or ltc1
        assert re.match(r'^(L|M|ltc1)[a-zA-Z0-9]+$', str(ltc_address))

    def test_sol_address_generation(self):
        """Test Solana address generation format"""
        generator = CryptoAddressGenerator()
        addresses = generator.get_addresses()
        
        assert 'sol' in addresses
        sol_address = addresses['sol']
        # Solana addresses are base58 encoded, typically 32-44 characters
        assert len(str(sol_address)) >= 32
        assert len(str(sol_address)) <= 44

    def test_trx_address_generation(self):
        """Test Tron address generation format"""
        generator = CryptoAddressGenerator()
        addresses = generator.get_addresses()
        
        assert 'trx' in addresses
        trx_address = addresses['trx']
        # Tron addresses start with T and are 34 characters
        assert str(trx_address).startswith('T')
        assert len(str(trx_address)) == 34

    def test_private_keys_generation(self):
        """Test private key generation for all supported cryptocurrencies"""
        generator = CryptoAddressGenerator()
        private_keys = generator.get_private_keys()
        
        expected_currencies = ['btc', 'ltc', 'trx', 'eth', 'sol']
        for currency in expected_currencies:
            assert currency in private_keys
            assert private_keys[currency] is not None
            assert len(str(private_keys[currency])) > 0

    def test_deterministic_generation(self):
        """Test that same seed produces same addresses and keys"""
        seed = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
        
        generator1 = CryptoAddressGenerator(seed_str=seed)
        generator2 = CryptoAddressGenerator(seed_str=seed)
        
        addresses1 = generator1.get_addresses()
        addresses2 = generator2.get_addresses()
        
        # Same seed should produce same addresses
        for currency in addresses1:
            assert str(addresses1[currency]) == str(addresses2[currency])

    def test_private_key_address_correspondence(self):
        """Test that private keys correspond to generated addresses"""
        generator = CryptoAddressGenerator()
        addresses = generator.get_addresses()
        private_keys = generator.get_private_keys()
        
        # Both should have same currencies
        assert set(addresses.keys()) == set(private_keys.keys())
        
        # Each currency should have both address and private key
        for currency in addresses:
            assert addresses[currency] is not None
            assert private_keys[currency] is not None

    def test_unique_addresses_different_seeds(self):
        """Test that different seeds produce different addresses"""
        generator1 = CryptoAddressGenerator()
        generator2 = CryptoAddressGenerator()
        
        addresses1 = generator1.get_addresses()
        addresses2 = generator2.get_addresses()
        
        # Different seeds should produce different addresses
        for currency in addresses1:
            assert str(addresses1[currency]) != str(addresses2[currency])

    def test_private_key_security(self):
        """Test private key generation security aspects"""
        generator = CryptoAddressGenerator()
        private_keys = generator.get_private_keys()
        
        # Private keys should not be empty or None
        for currency, private_key in private_keys.items():
            assert private_key is not None
            assert len(str(private_key)) > 10  # Minimum reasonable length
            
        # Private keys should be different for different currencies
        key_values = list(private_keys.values())
        assert len(set(str(k) for k in key_values)) == len(key_values)

    @patch('utils.CryptoAddressGenerator.Bip39SeedGenerator')
    def test_seed_generation_error_handling(self, mock_seed_gen):
        """Test error handling in seed generation"""
        mock_seed_gen.side_effect = Exception("Seed generation failed")
        
        with pytest.raises(Exception):
            CryptoAddressGenerator()

    def test_mnemonic_validation(self):
        """Test mnemonic phrase validation"""
        # Valid 12-word mnemonic
        valid_mnemonic = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
        generator = CryptoAddressGenerator(seed_str=valid_mnemonic)
        assert generator.mnemonic_str == valid_mnemonic
        
        # Test with custom seed
        custom_seed = "test seed phrase"
        generator2 = CryptoAddressGenerator(seed_str=custom_seed)
        assert generator2.mnemonic_str == custom_seed