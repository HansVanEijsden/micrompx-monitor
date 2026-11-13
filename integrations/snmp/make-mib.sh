#!/bin/sh
# Write a copy of MICROMPX-MIB.txt with your private enterprise number (PEN)
# filled in, ready to drop into a SNMP MIB directory.
#
# Usage: ./make-mib.sh <PEN> [output-directory]
# Example: ./make-mib.sh 12345 /usr/share/snmp/mibs
#          ./make-mib.sh 12345 .            # writes ./MICROMPX-MIB.txt
#
# Register a free PEN at https://pen.iana.org if you do not have one yet.
set -eu

PEN="${1:?give your private enterprise number, for example 12345}"
OUTDIR="${2:-.}"
DIR=$(dirname "$0")

case "$PEN" in
    ''|*[!0-9]*) echo 'PEN must be numeric' >&2; exit 1 ;;
esac

mkdir -p "$OUTDIR"
sed "s/{ enterprises 99999 }/{ enterprises $PEN }/" "$DIR/MICROMPX-MIB.txt" > "$OUTDIR/MICROMPX-MIB.txt"
echo "wrote $OUTDIR/MICROMPX-MIB.txt"
echo "agent-side base OID: 1.3.6.1.4.1.$PEN.1.1.1"
echo "test with: snmptranslate -M +$OUTDIR -m +MICROMPX-MIB MICROMPX-MIB::microMPXDecMeasuredLoss"
