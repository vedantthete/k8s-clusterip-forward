import os
import subprocess

class ChainNotFoundError(Exception):pass

def get_cluster_chain(cluster_ip, cluster_port):
    svc_rules = subprocess.check_output(
        'sudo iptables -t nat -S | grep "KUBE-SERVICES -d {}/32"'.format(
            cluster_ip),
        shell=True,
        text=True
    ).splitlines()
    for rule in svc_rules:
        if '--dport {} -j'.format(cluster_port) in rule:
            return rule.split(' ')[-1]
    raise ChainNotFoundError('Cluster chain not found')


def forward(service_name, cluster_ip, cluster_port, forwarded_port):
    
    try:
        cluster_chain = get_cluster_chain(cluster_ip, cluster_port)
        clusterip_forward_rule = subprocess.check_output(
            'sudo iptables -t nat -S | grep "forwarded for {} {}:{}"'.format(
                service_name, cluster_ip, cluster_port
                ),
            shell=True,
            text=True
        ).splitlines()[0]
        if not cluster_chain in clusterip_forward_rule or not cluster_ip in clusterip_forward_rule:
            clusterip_forward_rule = clusterip_forward_rule.replace('-A', '-D')
            print(clusterip_forward_rule)
            subprocess.check_output(
                "sudo iptables -t nat {}".format(clusterip_forward_rule),
                shell=True,
                text=True
            )
            new_rule = 'sudo iptables -t nat -I PREROUTING -p tcp --dport {} -m comment --comment "forwarded for {} {}:{}" -j {}'.format(
                forwarded_port, service_name,cluster_ip, cluster_port,
                cluster_chain
            )
            print(new_rule)
            subprocess.check_output(
                new_rule,
                shell=True, text=True
            )
        else:
            print("Valid rule | {} | exists, skipping".format(clusterip_forward_rule))
    except subprocess.CalledProcessError:
        print("Tables locked, skipping")
        pass
    except:
        new_rule = 'sudo iptables -t nat -I PREROUTING -p tcp --dport {} -m comment --comment "forwarded for {} {}:{}" -j {}'.format(
            forwarded_port, service_name,cluster_ip, cluster_port,
            cluster_chain
        )
        print(new_rule)
        subprocess.check_output(
            new_rule,
            shell=True, text=True
        )

service_name = os.environ.get('FORWARDED_SERVICE_NAME', 'nginx-service')
cluster_ip = os.environ.get('FORWARD_CLUSTER_IP', '10.110.145.49')
cluster_port = os.environ.get('FORWARD_CLUSTER_PORT', '30000')
forwarded_port = os.environ.get('FORWARD_TO_PORT', '80')


forward(service_name, cluster_ip, cluster_port, forwarded_port)
