import sys
import subprocess

def get_rules_by_comment(comment):
    rules = subprocess.check_output(
        'sudo iptables -t nat -S',
        shell=True,
        text=True
    ).splitlines()
    for rule in rules:
        if comment in rule:
            return rule
    return


def get_cluster_chain(namespace, service_name):
    comment = '{}/{} cluster IP'.format(namespace, service_name)
    svc_rule = get_rules_by_comment(comment)
    if not svc_rule:
        return
    return svc_rule.split(' ')[-1]


def forward(namespace, service_name, forward_port):
    cluster_chain = ''
    forward_rule_comment = "Port forwarded for service {}/{}".format(
        namespace, service_name)
    try:
        cluster_chain = get_cluster_chain(namespace, service_name)
        forward_rule = get_rules_by_comment(forward_rule_comment)
        if forward_rule:
            if not cluster_chain or not cluster_chain in forward_rule or not forward_port in forward_rule:
                delete_rule = 'sudo iptables -t nat ' + \
                    forward_rule.replace('-A', '-D')
                print("Running -> ", delete_rule)
                subprocess.check_output(
                    delete_rule,
                    shell=True,
                    text=True
                )
                return
            else:
                print("Rule exists, skipping -> ", forward_rule)
        elif cluster_chain:
            new_rule = 'sudo iptables -t nat -I PREROUTING -p tcp -m comment --comment "Port forwarded for service {}/{}" --dport {} -j {}'.format(
                namespace, service_name, forward_port, cluster_chain
            )
            print("Running -> ", new_rule)
            subprocess.check_output(
                new_rule,
                shell=True,
                text=True
            )
        else:
            print("Cluster chain not found ", namespace, service_name, forward_port)
    except Exception:
        print("Iptables locked, skipping")

namespace, service_name, forwarded_port = sys.argv[1:]

forward(namespace, service_name, forwarded_port)
