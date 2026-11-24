"""One try per run: ask Oracle for the Always Free Ampere VM (2 OCPU / 12 GB) named flow-studio.
Runs every ~10 min from GitHub Actions. Never prints IDs or keys (this repo is public)."""
import os, sys, oci

cfg = {
    'user': os.environ['OCI_USER'], 'fingerprint': os.environ['OCI_FINGERPRINT'],
    'tenancy': os.environ['OCI_TENANCY'], 'region': os.environ.get('OCI_REGION', 'ap-mumbai-1'),
    'key_content': os.environ['OCI_KEY'],
}
T = cfg['tenancy']
nr = oci.retry.NoneRetryStrategy()
comp = oci.core.ComputeClient(cfg, retry_strategy=nr)
net = oci.core.VirtualNetworkClient(cfg)
ident = oci.identity.IdentityClient(cfg)

live = [i for i in comp.list_instances(T).data
        if i.display_name == 'flow-studio' and i.lifecycle_state not in ('TERMINATED', 'TERMINATING')]
if live:
    print('VM already exists:', live[0].lifecycle_state, '- nothing to do')
    sys.exit(0)

AD = ident.list_availability_domains(T).data[0].name
vcn = [v for v in net.list_vcns(T).data if v.display_name == 'flow-vcn'][0]
sub = net.list_subnets(T, vcn_id=vcn.id).data[0]
img = comp.list_images(T, operating_system='Canonical Ubuntu', operating_system_version='22.04',
                       shape='VM.Standard.A1.Flex', sort_by='TIMECREATED', sort_order='DESC').data[0]
try:
    comp.launch_instance(oci.core.models.LaunchInstanceDetails(
        compartment_id=T, availability_domain=AD, display_name='flow-studio', shape='VM.Standard.A1.Flex',
        shape_config=oci.core.models.LaunchInstanceShapeConfigDetails(ocpus=2, memory_in_gbs=12),  # Always Free max
        source_details=oci.core.models.InstanceSourceViaImageDetails(image_id=img.id, boot_volume_size_in_gbs=50),
        create_vnic_details=oci.core.models.CreateVnicDetails(subnet_id=sub.id, assign_public_ip=True),
        metadata={'ssh_authorized_keys': os.environ['SSH_PUBKEY']}))
    print('LAUNCHED flow-studio (2 OCPU / 12 GB, Always Free)')
except oci.exceptions.ServiceError as e:
    print('Not yet:', e.status, e.message.split('.')[0])
