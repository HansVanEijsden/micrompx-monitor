#!/bin/sh
# Write a copy of MICROMPX-MIB.txt with your private enterprise number (PEN)
# filled in, ready to drop into a SNMP MIB directory.
#
# Usage: ./make-mib.sh <PEN> [output-directory] [sub-identifier]
# Example: ./make-mib.sh 12345 /usr/share/snmp/mibs
#          ./make-mib.sh 12345 /usr/share/snmp/mibs 2
#          ./make-mib.sh 12345 .            # writes ./MICROMPX-MIB.txt
#
# The optional third argument puts the tree one level deeper, under
# PEN.<sub> instead of PEN. Use it when the PEN already carries another
# device tree; the agent-side base OID becomes
# 1.3.6.1.4.1.<PEN>.<sub>.1.1.1.
#
# Register a free PEN at https://pen.iana.org if you do not have one yet.
set -eu

PEN="${1:?give your private enterprise number, for example 12345}"
OUTDIR="${2:-.}"
SUB="${3:-}"
DIR=$(dirname "$0")

case "$PEN" in
    ''|*[!0-9]*) echo 'PEN must be numeric' >&2; exit 1 ;;
esac

if [ -n "$SUB" ]; then
    case "$SUB" in
        *[!0-9]*) echo 'sub-identifier must be numeric' >&2; exit 1 ;;
    esac
    ORG="{ enterprises $PEN $SUB }"
    BASE="1.3.6.1.4.1.$PEN.$SUB.1.1.1"
else
    ORG="{ enterprises $PEN }"
    BASE="1.3.6.1.4.1.$PEN.1.1.1"
fi

if ! grep -q '{ enterprises 99999 }' "$DIR/MICROMPX-MIB.txt"; then
    echo "MICROMPX-MIB.txt does not contain the { enterprises 99999 } placeholder" >&2
    exit 1
fi

mkdir -p "$OUTDIR"
sed "s/{ enterprises 99999 }/$ORG/" "$DIR/MICROMPX-MIB.txt" > "$OUTDIR/MICROMPX-MIB.txt"
echo "wrote $OUTDIR/MICROMPX-MIB.txt"
echo "agent-side base OID: $BASE"
echo "test with: snmptranslate -M +$OUTDIR -m +MICROMPX-MIB MICROMPX-MIB::microMPXDecMeasuredLoss"
