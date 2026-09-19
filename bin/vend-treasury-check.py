# Vend daily treasury check — called by revenue-track
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from nano_verify import get_account_info
    acct = os.environ.get('NANO_AGENT_ACCOUNT', '')
    if not acct:
        print("NO_ACCOUNT")
        sys.exit(0)
    info = get_account_info(acct)
    if info:
        balance = int(info.get('balance', '0'))
        pending = int(info.get('pending', '0'))
        print(f'balance_raw={balance} pending_raw={pending} balance_xno={balance/1e30:.6f} pending_xno={pending/1e30:.6f}')
    else:
        print('UNREACHABLE')
except Exception as e:
    print(f'UNREACHABLE: {e}')