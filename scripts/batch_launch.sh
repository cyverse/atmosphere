USER="$1"
# Examples:
#MACHINE_ALIAS="1111-2222-3333-4444"
#MACHINE_ALIAS="1111-2222-3333-4444,1234-1234-1234-1234"
MACHINE_ALIAS='most_used'  # Launch some subset of the 'most used' machines for that provider.
cd /opt/dev/atmosphere/scripts
. /opt/env/atmo/bin/activate
./launch_instances.py --provider-id 4 --size tiny1 --machine-alias $MACHINE_ALIAS --user $USER
./launch_instances.py --provider-id 5 --size tiny1 --machine-alias $MACHINE_ALIAS --user $USER
./launch_instances.py --provider-id 6 --size tiny --machine-alias $MACHINE_ALIAS --user $USER
