s#!/usr/bin/python3
''' Assembles the WRAMP Code into Binary Source '''

import os
import re
import pdb
import sys
from collections import namedtuple


JUMP_LENGTH = 20
OFFSET_LENGTH = 16


# Different Command Patterns 
WHITESPACE_PATTERN = re.compile(r'^\s*$')
COMMENT_PATTERN = re.compile(r'^\s*\#')
LABEL_PATTERN = re.compile(r'[a-zA-Z0-9]*:$')
WORD_PATTERN = re.compile(r'^\.word\s*\d*')


COMMAND_STRUCT = namedtuple("COMMAND_STRUCT", "ass_pattern binary_format process_function")
WORD_LENGTH = 4



#
# Utility Functions
#
def convert_twos_compliment(string_num, length):
    try:
        int_num = int(string_num, 0)
        bin_str = bin(int_num % (1<<length))[2:]
        return int(bin_str, 2) 
    except:
        return False



def convert_to_bin(bin_string):
    ''' Converts the String of 1/0's Binary ''' 
    bin_string = bin_string.replace(' ', '')
    bin_value = int(bin_string, 2).to_bytes(4, 'little')
    return bin_value





#
# Process Commands
#

def process_rtype(t_obj, line):
    ''' This function is used to assemble the R-Type WRAMP Commands '''
    pattern = re.compile(t_obj.ass_pattern)
    match = pattern.match(line)
    rd = match.group(1)
    rs = match.group(2)
    rt = match.group(3)
    bin_str = t_obj.binary_format.format(int(rd), int(rs), int(rt))

    return bin_str


def process_itype(t_obj, line):
    ''' This function is used to assemble the I-Type WRAMP Commands '''
    pattern = re.compile(t_obj.ass_pattern)
    match = pattern.match(line)
    rd = match.group(1)
    rs = match.group(2)
    imm = match.group(3)
    bin_str = t_obj.binary_format.format(int(rd), int(rs), int(imm, 0)) # TODO Don't forget about negative numbers
    return bin_str

def process_jtype(t_obj, line):    # TODO don't forget about testing with labels being declared after they;re used
    # Group Command Sections
    command = t_obj.ass_pattern.split()[0]
    pattern = re.compile(t_obj.ass_pattern)
    match = pattern.match(line)
    
    if(command == 'bnez' or command == 'beqz'): # Labels
        # Convert BNEZ / BEQZ commands to assembly
        rs = match.group(1)
        imm = convert_twos_compliment(match.group(2), JUMP_LENGTH) # Adjusting for label line
        bin_str = t_obj.binary_format.format(int(rs), int(imm))

        # TODO DOuble Check functionalty
        return bin_str
    
    elif(command == 'lw' or command == 'sw'):
        # Convert LW / SW commands to assembly
        rd = match.group(1)
        rs = match.group(3)
        imm = convert_twos_compliment(match.group(2), JUMP_LENGTH)
        bin_str = t_obj.binary_format.format(int(rd), int(rs), int(imm))
        # TODO 
        return bin_str

    elif(command == 'j'):
        imm = convert_twos_compliment(match.group(1), OFFSET_LENGTH) 
        bin_str = t_obj.binary_format.format(int(imm)) 
        #TODO DOUBLE CHECK
        return bin_str;



# Instruction Table [Blueprints]
instruction_table = {
    # R Commands
    COMMAND_STRUCT( 'add \$(\d+),\$(\d+),\$(\d+)',              '0000 {:04b} {:04b} 0000 0000 0000 0000 {:04b}',   process_rtype ),
    COMMAND_STRUCT( 'sub \$(\d+),\$(\d+),\$(\d+)',              '0000 {:04b} {:04b} 0010 0000 0000 0000 {:04b}',   process_rtype ),
    COMMAND_STRUCT( 'and \$(\d+),\$(\d+),\$(\d+)',              '0000 {:04b} {:04b} 1011 0000 0000 0000 {:04b}',   process_rtype ),
    COMMAND_STRUCT( 'xor \$(\d+),\$(\d+),\$(\d+)',              '0000 {:04b} {:04b} 1111 0000 0000 0000 {:04b}',   process_rtype ),
    COMMAND_STRUCT( 'or \$(\d+),\$(\d+),\$(\d+)' ,              '0000 {:04b} {:04b} 1101 0000 0000 0000 {:04b}',   process_rtype ),
    # I Commands
    COMMAND_STRUCT( 'addi \$(\d+),\$(\d+),((?:0b|0x|-)?\S+)',   '0001 {:04b} {:04b} 0000 {:016b}',                 process_itype ),
    COMMAND_STRUCT( 'subi \$(\d+),\$(\d+),((?:0b|0x|-)?\S+)',   '0001 {:04b} {:04b} 0010 {:016b}',                 process_itype ),
    COMMAND_STRUCT( 'andi \$(\d+),\$(\d+),((?:0b|0x|-)?\S+)',   '0001 {:04b} {:04b} 1011 {:016b}',                 process_itype ),
    COMMAND_STRUCT( 'xori \$(\d+),\$(\d+),((?:0b|0x|-)?\S+)'    '0001 {:04b} {:04b} 1111 {:016b}',                 process_itype ),
    COMMAND_STRUCT( 'ori \$(\d+),\$(\d+),((?:0b|0x|-)?\S+)',    '0001 {:04b} {:04b} 1101 {:016b}',                 process_itype ),
    # J Commands
    COMMAND_STRUCT( 'lw \$(\d+),(\S+)\(\$(\d+)\)'  ,            '1000 {:04b} {:04b} {:020b}',                      process_jtype ),
    COMMAND_STRUCT( 'sw \$(\d+),(\S+)\(\$(\d+)\)'  ,            '1001 {:04b} {:04b} {:020b}',                      process_jtype ),
    COMMAND_STRUCT( 'j (\S+)'   ,                               '0100 0000 0000 {:020b}',                          process_jtype ),
    COMMAND_STRUCT( 'bnez \$(\d+),(\S+)',                       '1011 0000 {:04b} {:020b}',                        process_jtype ),
    COMMAND_STRUCT( 'beqz \$(\d+),(\S+)',                       '1010 0000 {:04b} {:020b}',                        process_jtype ),
}


def pre_process(file):
    '''pre-processes the file and returns a list of all commands in order'''
    commands_list = []
    labels = {}
    instruction_number = 0

    # Populate Label / PC Dictionary
    with open(file) as file_object:
        for inx,line in enumerate(file_object):
            # Remove all whitespace + Comments
            line = line.strip()
            if WHITESPACE_PATTERN.match(line) or COMMENT_PATTERN.match(line):
                continue

            # Adding Label
            if(LABEL_PATTERN.match(line)):
                labels[line.strip(':')] = instruction_number
                continue
            else:
                commands_list.append(line)
            # Increase PC Count
            instruction_number += 1
    return (labels, commands_list)
    



#
# Main Functions
#


def replace_label(line, label_dict, pc):
    command = line.split()[0]
    # Try/catch looking for labels and replace where possible 
    if(command == 'bnez' or command == 'beqz'):
        try:
            val = int(re.split("\,|\ ", line)[2], 0)
        except ValueError:
            val = re.split("\,|\ ", line)[2]
            off = label_dict[val] - pc
            line = line.split(',')[0] + "," + str(off)  
    elif(command == 'j'):
        try:
            val = int(line.split()[1])
        except ValueError:
            val = line.split()[1]
            line = line.split()[0] + " " + str(label_dict[val])  

    return line;

def assembler(f_input, f_output):
    ''' This function is used to assemble the binary code '''
    #Allocate Variables
    bin_instructions = []
    
    # Get Labels and Commands
    (label_dict, assembly_instructions) = pre_process(f_input)
    
    # Iterate over all commands and convert to a binary form
    for inx, line in enumerate(assembly_instructions):
        inx += 1
        # Replace Labels       
        line = replace_label(line, label_dict, inx);
        
        # Check for .word directive 
        if(WORD_PATTERN.match(line)):
            # Convert hex value to binary string and add to list
            bin_str = bin(int(line.split()[1], 0))[2:]
            bin_str = "{:032b}".format(int(bin_str, 2))
            bin_instructions.append(convert_to_bin(bin_str))
            continue
        
        # Iterate over instruction-table finding match
        for t_instruction in instruction_table:
                pattern = re.compile(t_instruction.ass_pattern)
                match = pattern.match(line)

                if match == None: # Not this command 
                    continue;

                # Call the instruction function
                bin_command = t_instruction.process_function(t_instruction, line)
                bin_instructions.append(convert_to_bin(bin_command))
                break;
        
        if(match == None): # No match found
            print(line)
            print("There is an issue on line {:d}. Unrecognised command. Skipping.")

    # Write Byte Array to output file
    with open(f_output, 'wb') as file_object:
        for instruction in bin_instructions:
            file_object.write(instruction)



def main(argc, argv):
    ''' This is the main fucntion of the application'''
    f_input = argv[1]
    f_output = argv[2]
    assembler(f_input, f_output)

if __name__ == "__main__":
    main(len(sys.argv), sys.argv)
