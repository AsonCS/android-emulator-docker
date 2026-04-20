import pexpect

child = pexpect.spawn('su')
child.expect('Password:')
child.sendline('root')
child.expect('#') # Wait for root prompt
child.sendline('chmod -R 666 /dev/kvm')
child.expect('#')
child.sendline('exit')
