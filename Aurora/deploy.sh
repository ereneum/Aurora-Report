#!/bin/sh
near delete attacker.test.near test.near
near create-account attacker.test.near --master-account=test.near --initial-balance 1000000
near delete aurora.test.near test.near
near create-account aurora.test.near --master-account=test.near --initial-balance 1000000
aurora install --chain 1313161556 --owner aurora.test.near --signer aurora.test.near mainnet-test.wasm
aurora get-version
aurora encode-address attacker.test.near
near call aurora.test.near mint_account --base64 --args 'MnJaZZGSutQJJ5OWn+M5TbhHno0AAAAAAAAAAAAAZKeztuAN' --accountId test.near --gas 100000000000000
near view aurora.test.near ft_balance_of --args '{"account_id": "aurora.test.near"}'
aurora get-balance 0x32725A659192bAD4092793969fE3394Db8479E8D
near view aurora.test.near ft_total_eth_supply_on_aurora
near view aurora.test.near ft_total_eth_supply_on_near

