add $0,$1,$2
sub $3,$4,$5
and $6,$7,$8

.word 0x00100002
.word 0x03420005
.word 0x067b0008
.word 0xFEEDBEEF

andi $3,$4,0b1111111111111111
xori $5,$6,0xF0F0
ori $7,$8,12345

