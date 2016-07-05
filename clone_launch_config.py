#!/usr/bin/env python

"""
Process to clone a launch configuration in AWS with various twiddles.

NOTE: requires that your shell enviornment be setup to access AWS
with variables of AWS_DEFAULT_REGION, AWS_ACCESS_KEY_ID and
AWS_SECRET_ACCESS_KEY
"""

from __future__ import print_function, division, absolute_import, unicode_literals

import argparse
import os
import sys
import traceback

import boto.ec2.autoscale


def parse_user_data(infile):
    """argparse data type builder to transform a file into a string."""
    if os.path.isfile(infile):
        with open(infile, 'r') as inf:
            out = inf.read()
    else:
        sys.exit("File not found: {}".format(infile))
    return out


def parse_cli(passed_args=None):
    """Parse the CLI.  The goal is to turn each argument into None, or the value
    passed in on the CLI.  These values will later be merged with the existing
    LC's values. Key insight: Each value in the resulting 'args' namespace will
    be named exactly that as AWS/Boto uses."""
    if passed_args is None:
        passed_args = sys.argv[1:]
    parser = argparse.ArgumentParser(description="Clone a Launch Configuration."
                                     " Note: Any options passed will override"
                                     " the cloned LCs settings, rather than"
                                     " append to them."
                                     " Note2: Requires shell variables to be"
                                     " set: AWS_DEFAULT_REGION,"
                                     " AWS_ACCESS_KEY_ID, and"
                                     " AWS_SECRET_ACCESS_KEY"
                                     )
    parser.add_argument("old_lc_name", action='store',
                        help="The name of the LC to clone.")
    parser.add_argument("new_lc_name", action='store',
                        help="The new LC name.")
    parser.add_argument("--ami", action='store',
                        dest='image_id', default=None,
                        help="The AMI ID for the launch config")
    parser.add_argument("--ssh-key", action='store',
                        dest='key_name', default=None,
                        help="The SSH for the launch config")
    parser.add_argument("--security-group", action='append',
                        dest='security_groups',
                        help="The (or one of the) security group for the LC."
                             " May be specified multiple times")
    parser.add_argument("--user-data-script", action='store',
                        type=parse_user_data, default=None, dest='user_data',
                        help="The file containing the user data script")
    parser.add_argument("--instance-type", action='store',
                        default=None,
                        help="The instance type")
    parser.add_argument("--enable-instance-monitoring", action='store_const',
                        const=True, default=None, dest='instance_monitoring',
                        help="enable instance-monitoring")
    parser.add_argument("--disable-instance-monitoring", action='store_const',
                        const=False, default=None, dest='instance_monitoring',
                        help="enable instance-monitoring")
    parser.add_argument("--spot-price", action='store',
                        type=float, default=None,
                        help="The spot price")
    parser.add_argument("--instance-profile-name", action='store',
                        default=None,
                        help="The name (or ARN) of the instance profile for"
                             " these instances")
    parser.add_argument("--enable-ebs-optimized", action='store_const',
                        const=True, default=None, dest='ebs_optimized',
                        help="enable ebs optimized")
    parser.add_argument("--disable-ebs-optimized", action='store_const',
                        const=False, default=None, dest='ebs_optimized',
                        help="enable ebs optimized")
    parser.add_argument("--enable-associate-public-ip-address", action='store_const',
                        const=True, default=None, dest='associate_public_ip_address',
                        help="enable association of public ip addresses")
    parser.add_argument("--disable-associate-public-ip-address", action='store_const',
                        const=False, default=None, dest='associate_public_ip_address',
                        help="enable association of public ip addresses")
    parser.add_argument("--region", action='store',
                        default=os.environ['AWS_DEFAULT_REGION'],
                        help="region within which to clone")
    args = parser.parse_args(passed_args)
    return args


def merge_lcs(old_lc, args):
    """Build a new boto LC object (Note: a different function builds the live AWS
    version).  Uses a bunch of terniary statements to make each value a clone
    of the old one, unless the CLI overrides it."""
    lc_name = args.new_lc_name
    image_id = old_lc.image_id if args.image_id is None else args.image_id
    key_name = old_lc.key_name if args.key_name is None else args.key_name
    security_groups = old_lc.security_groups if args.security_groups is None else args.security_groups
    user_data = old_lc.user_data if args.user_data is None else args.user_data
    instance_type = old_lc.instance_type if args.instance_type is None else args.instance_type
    instance_monitoring = old_lc.instance_monitoring if args.instance_monitoring is None else args.instance_monitoring
    spot_price = old_lc.spot_price if args.spot_price is None else args.spot_price
    instance_profile_name = old_lc.instance_profile_name if args.instance_profile_name is None else args.instance_profile_name
    ebs_optimized = old_lc.ebs_optimized if args.ebs_optimized is None else args.ebs_optimized
    associate_public_ip_address = old_lc.associate_public_ip_address if args.associate_public_ip_address is None else args.associate_public_ip_address
    try:
        lc = boto.ec2.autoscale.LaunchConfiguration(name=lc_name,
                                                    image_id=image_id,
                                                    key_name=key_name,
                                                    security_groups=security_groups,
                                                    user_data=user_data,
                                                    instance_type=instance_type,
                                                    instance_monitoring=instance_monitoring,
                                                    spot_price=spot_price,
                                                    instance_profile_name=instance_profile_name,
                                                    ebs_optimized=ebs_optimized,
                                                    associate_public_ip_address=associate_public_ip_address,
                                                    )
    except:
        print("FATAL ERROR:")
        traceback.print_exc(file=sys.stdout)
        sys.exit("Failed to create launch config object in boto")
    return lc


def botoconn(args):
    """builds the boto connection object"""
    try:
        return boto.ec2.autoscale.connect_to_region(args.region)
    except:
        print("FATAL ERROR:")
        traceback.print_exc(file=sys.stdout)
        sys.exit("Failed to connect to AWS. Did you set the shell vars right?")


def get_lc(args, conn):
    """Gets the existing LC for cloaning"""
    try:
        lc = conn.get_all_launch_configurations(names=[args.old_lc_name, ])[0]
    except:
        print("FATAL ERROR:")
        traceback.print_exc(file=sys.stdout)
        sys.exit("Failed to get source LC")
    return lc


def create_lc(new_lc, conn):
    """Actually creates the LC within AWS"""
    try:
        conn.create_launch_configuration(new_lc)
        # print("would create here")
    except:
        print("FATAL ERROR:")
        traceback.print_exc(file=sys.stdout)
        sys.exit("Failed to create new LC")


def pre_check():
    """Validates that the environment is setup right."""
    try:
        x = os.environ['AWS_DEFAULT_REGION']
    except KeyError:
        print("FATAL ERROR:")
        traceback.print_exc(file=sys.stdout)
        sys.exit("Please set your shell variables for AWS access")
    del x


def main():
    pre_check()
    args = parse_cli()
    conn = botoconn(args)
    old_lc = get_lc(args, conn)
    new_lc = merge_lcs(old_lc, args)
    create_lc(new_lc, conn)


if __name__ == "__main__":
    main()
