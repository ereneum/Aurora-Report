#!/usr/bin/python3
import sys, base64, struct
address, nonce, balance = sys.argv[1:4]
account = sys.argv[4] if len(sys.argv) > 4 else 'test.near'
args = base64.b64encode(bytes.fromhex(address) + struct.pack('<QQ', int(nonce), int(balance)))
cmd = "near call aurora.test.near mint_account --base64 --args '%s' --accountId %s --gas 100000000000000" % (args.decode('utf-8'), account)
print(cmd)

