"""Install or refresh four detailed IT Knowledge Base articles.

Run from backend using your virtual-environment Python interpreter.
Safe to rerun; preserves all other articles and tickets.
"""
from app import app, db, KnowledgeArticle, utc_now

ARTICLES = [
    {
        'title': 'Unable to Connect to Office Wi-Fi Network',
        'category': 'Network',
        'summary': 'Diagnose Wi-Fi connection failures on office laptops, including network credentials, wireless adapters, signal problems, and connectivity outages.',
        'keywords': 'wifi, wi-fi, wireless, network, internet, router, office wifi, cannot connect, connection, adapter, access point',
        'content': '''OVERVIEW
Employees may be unable to join the office wireless network because of invalid credentials, disabled adapters, weak signals, outdated drivers, or a temporary network outage.

TROUBLESHOOTING STEPS
1. Verify Wi-Fi is enabled on the laptop or workstation.
2. Make sure Airplane Mode is switched off.
3. Confirm the user selected the correct authorized office Wi-Fi network (SSID).
4. Disconnect and reconnect using approved company credentials. Never ask the user to send a password in a ticket.
5. Restart the laptop and test the connection again.
6. Ask whether colleagues can connect to the same network. This helps distinguish a device issue from an office-wide outage.
7. Run Windows Network Troubleshooter and record its diagnostic message.
8. If the issue continues, have the Network Support Team inspect the wireless adapter, access point, authentication, and network availability.

EXPECTED RESULT
The device connects to the authorized office Wi-Fi and can access company services and the internet.

ESCALATION
Escalate to Network Support immediately if multiple employees are affected. Record the location, SSID, error message, and time the issue began.'''
    },
    {
        'title': 'Troubleshooting Slow Computer Performance',
        'category': 'Hardware',
        'summary': 'Diagnose slow Windows laptops and desktops caused by memory pressure, background processes, disk usage, startup software, or hardware faults.',
        'keywords': 'slow, laptop, computer, freezing, freezes, performance, lag, memory, ram, cpu, disk, startup, excel, chrome',
        'content': '''OVERVIEW
An employee computer may become unresponsive because of high CPU or memory use, limited storage, excessive startup software, unwanted programs, or hardware problems.

TROUBLESHOOTING STEPS
1. Ask the employee to save any open work, then restart the computer.
2. Open Task Manager with Ctrl + Shift + Esc.
3. Review CPU, memory, and disk utilization for unusually high or persistent usage.
4. Close unnecessary programs after saving work; do not terminate company security tools.
5. Check free space on the system drive.
6. Disable unnecessary startup apps only when permitted by company policy.
7. Install approved Windows and application updates.
8. Run the organization's approved antivirus or endpoint security scan.
9. If the device remains slow, collect the system specifications and diagnostic information and escalate for deeper investigation.

EXPECTED RESULT
Common office programs open normally, the system responds promptly, and performance remains stable during typical work.

ESCALATION
Escalate to Desktop Support if utilization stays abnormally high, the device frequently freezes, or hardware errors are detected.'''
    },
    {
        'title': 'Microsoft Outlook Unable to Send or Receive Emails',
        'category': 'Software',
        'summary': 'Troubleshoot Outlook email delivery and synchronization problems, including offline mode, network access, mailbox limits, and service outages.',
        'keywords': 'outlook, email, mail, emails, inbox, sync, synchronization, receive, send, mailbox, exchange, offline',
        'content': '''OVERVIEW
Microsoft Outlook may stop sending or receiving messages because of connectivity issues, Offline Mode, mailbox limits, authentication errors, or an email service disruption.

TROUBLESHOOTING STEPS
1. Confirm that the device has working internet access.
2. Verify that Outlook is not set to Work Offline.
3. Close Outlook, reopen it, and retry sending or receiving a test message.
4. Sign in to the organization's approved webmail portal to determine whether the problem is isolated to the desktop app.
5. Check whether the mailbox is full or near its storage quota.
6. Record any errors shown by Outlook; avoid including private email content in the support ticket.
7. Verify with IT that the user's account remains active and permitted to access email.
8. If the issue persists, send the error details to the Email Administration Team.

EXPECTED RESULT
Outlook can send and receive mail reliably, and new messages appear without repeated synchronization errors.

ESCALATION
If several employees are affected or webmail is also unavailable, escalate as a potential email service outage.'''
    },
    {
        'title': 'Employee Account Locked or Unable to Log In',
        'category': 'Access',
        'summary': 'Restore access to a locked or inaccessible employee account using approved identity verification and password reset procedures.',
        'keywords': 'account, locked, login, log in, sign in, password, reset, credentials, access, disabled, authentication',
        'content': '''OVERVIEW
Employees can lose account access after repeated failed sign-in attempts, expired credentials, identity verification failures, or account suspension.

TROUBLESHOOTING STEPS
1. Confirm the correct username or employee sign-in ID is being used.
2. Check that Caps Lock and keyboard layout are correct.
3. Verify network connectivity if signing in requires online authentication.
4. Use the organization's official self-service password reset portal when available.
5. Complete identity verification according to company policy.
6. If the account remains locked, contact the IT Helpdesk using the approved support channel.
7. An authorized administrator should review account state and unlock or reset it only after verifying the person's identity.
8. If lockouts continue, investigate the cause and review security logs according to policy.

EXPECTED RESULT
The employee regains access to approved systems using their own credentials and normal security controls.

SECURITY AND ESCALATION
Never request a password, MFA code, or recovery secret in a support ticket. Escalate repeated unexplained lockouts or suspicious activity to the security team.'''
    },
]

# Keep earlier Phase 4 seed article IDs, where appropriate, so existing links work.
OLD_TITLES = {
    'Unable to Connect to Office Wi-Fi Network': 'Wi-Fi connection troubleshooting',
    'Employee Account Locked or Unable to Log In': 'Reset a locked account password',
}


def main():
    with app.app_context():
        db.create_all()
        created = updated = 0
        for item in ARTICLES:
            existing = db.session.execute(
                db.select(KnowledgeArticle).where(KnowledgeArticle.title == item['title'])
            ).scalar_one_or_none()
            if existing is None and item['title'] in OLD_TITLES:
                existing = db.session.execute(
                    db.select(KnowledgeArticle).where(KnowledgeArticle.title == OLD_TITLES[item['title']])
                ).scalar_one_or_none()
            if existing:
                for field, value in item.items():
                    setattr(existing, field, value)
                existing.published = True
                existing.updated_at = utc_now()
                updated += 1
            else:
                db.session.add(KnowledgeArticle(**item, published=True))
                created += 1
        db.session.commit()
        print(f'Knowledge Base update complete: {created} created, {updated} refreshed.')
        print('Other articles, users, tickets, SLA rules, and messages were not changed.')


if __name__ == '__main__':
    main()
