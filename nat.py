import sys
import subprocess
from time import sleep


class Rule:
    def __init__(self, namespace, service, forward_port):
        self.namespace = namespace
        self.service = service
        self.forward_port = forward_port
        self.created_rules = []

    def get_rules_by_chain_comment(self, chain, comment):
        rules = subprocess.check_output(
            'sudo iptables -t nat -S',
            shell=True,
            text=True
        ).splitlines()
        matched_rules = []
        for rule in rules:
            if comment in rule and chain in rule:
                matched_rules.append(rule)
        return matched_rules

    def get_rule_target(self, clusterip_rule):
        return clusterip_rule.split(' ')[-1]

    def get_expected_rule(self, clusterip_rule_target):
        rule = '-A PREROUTING -p tcp -m comment --comment "Port forwarded for service {}/{}" -m tcp --dport {} -j {}'.format(
            self.namespace, self.service, self.forward_port, clusterip_rule_target
        )
        return rule

    def delete_rule(self, rule):
        rule = 'sudo iptables -t nat '+rule.replace('-A', '-D')
        print("DELETING -> ", rule)
        return subprocess.check_output(
            rule,
            shell=True,
            text=True
        )

    def cleanup(self):
        existing_rules = self.get_rules_by_chain_comment('PREROUTING', "Port forwarded for service {}/{}".format(
            self.namespace, self.service))
        while existing_rules:
            rule_delete = 'sudo iptables -t nat ' + \
                existing_rules[-1].replace('-A', '-D')
            print("Cleaning up -> ", rule_delete)
            try:
                subprocess.check_output(
                    rule_delete,
                    shell=True,
                    text=True
                )
                existing_rules.pop()
            except Exception as e:
                if 'No chain' in e.output:
                    existing_rules.pop()
                else:
                    sleep(1)

    def create_rule(self, rule):
        self.cleanup()
        rule = 'sudo iptables -t nat ' + rule.replace('-A', '-I')
        print("CREATING -> ", rule)
        subprocess.check_output(
            rule,
            shell=True,
            text=True
        )
        return rule

    def create(self):
        clusterip_rule_comment = '{}/{} cluster IP'.format(
            self.namespace, self.service)
        forward_rule_comment = "Port forwarded for service {}/{}".format(
            self.namespace, self.service)
        try:
            service_clusterip_rule = self.get_rules_by_chain_comment(
                'KUBE-SERVICES',
                clusterip_rule_comment
            )
            service_clusterip_rule = service_clusterip_rule[0] if service_clusterip_rule else ''

            service_clusterip_rule_target = self.get_rule_target(
                service_clusterip_rule)

            expected_forward_rule = self.get_expected_rule(
                service_clusterip_rule_target)

            service_forward_rule_in_os = self.get_rules_by_chain_comment(
                'PREROUTING',
                forward_rule_comment
            )
            service_forward_rule_in_os = service_forward_rule_in_os[
                0] if service_forward_rule_in_os else ''

            if not service_forward_rule_in_os:
                self.create_rule(expected_forward_rule)
            elif service_forward_rule_in_os != expected_forward_rule:
                print(service_forward_rule_in_os)
                print(expected_forward_rule)
                self.delete_rule(service_forward_rule_in_os)
            else:
                print("Forward rule exists, skipping")
        except Exception as e:
            print(e)
            print("Iptables locked, skipping")


namespace, service_name, forwarded_port, wait_for = sys.argv[1:]

rule = Rule(namespace, service_name, forwarded_port)
try:
    rule.cleanup()
except:
    pass
if float(wait_for) < 0:
    exit()
while True:
    rule.create()
    sleep(float(wait_for) or 15)
