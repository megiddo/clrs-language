#/bin/sh

sed -i -e 's/<-/←/g' $1
sed -i -e 's/<->/↔/g' $1
sed -i -e 's/←>/↔/g' $1

sed -i -e 's/|>/▷/g' $1

sed -i -e 's/\s\.Inf\s/∞/g' $1

sed -i -e 's/|\./⌊/g' $1
sed -i -e 's/\.|/⌋/g' $1

sed -i -e 's/|^/⌈/g' $1
sed -i -e 's/^|/⌉/g' $1