#!/usr/bin/python3
''' Disassembles the Binary Code into WRAMP Assembly '''

import os
import re
import sys
from struct import *
from collections import namedtuple
import pdb

# Public 
COMMAND_STRUCT = namedtuple("COMMAND_STRUCT", "ass_command binary_pattern process_function")
LABELS = []
WORD_LENGTH = 4


#
# Utility Functions
#

def is_int(value):
    ''' Tests whether a value can be cast to an int '''
    try:
        return int(value)
    except:
        return False

def convert_twos_compliment(bin_str):
    """ Converts a string of binary numbers to their two's compliment integer representation """
    length = len(bin_str)

    if(bin_str[0] == '0'):
        return int(bin_str, 2)
    else:
        return int(bin_str, 2) - (1 << length)  

#
# Process Commands
#

def process_rtype_command(r_string, line_num, t_obj):
    ''' This function is used to disassemble the R-Type WRAMP Commands '''
    # Use the instruction table for grouping regex tokens 
    pattern = re.compile(t_obj.binary_pattern)
    match = pattern.match(r_string)
    rd = match.group(1)
    rs = match.group(2)
    rt = match.group(3)
    # Build instruction from instructon format and add to instruction list
    command = t_obj.ass_command.format(int(rd, 2), int(rs, 2), int(rt, 2))
    return command

def process_itype_command(r_string, line_num, t_obj):
    ''' This function is used to disassemble the I-Type WRAMP Commands '''
    # Use the instruction table for grouping regex tokenss
    pattern = re.compile(t_obj.binary_pattern)
    match = pattern.match(r_string)
    rd = match.group(1)
    rs = match.group(2)
    imm = match.group(3)
    # Build instruction from instructon format and add to instruction list
    command = t_obj.ass_command.format(int(rd, 2), int(rs, 2), int(imm, 2))
    return command

def process_jtype_command(r_string, line_num, t_obj):
    ''' This function is used to disassemble the J-Type WRAMP Commands '''
    global LABELS
    # Compiling the regex
    command = t_obj.ass_command.split()[0]
    pattern = re.compile(t_obj.binary_pattern)
    match = pattern.match(r_string)
    
    if command == "lw" or command == "sw":
        # Convert LW / SW commands to assembly
        rd = match.group(1)
        rs = match.group(2)
        imm = convert_twos_compliment(match.group(3))
        command = t_obj.ass_command.format(int(rd, 2), imm, int(rs, 2))
    elif command == 'bnez' or command == 'beqz': 
        # Convert BNEZ / BEQZ commands to assembly
        rs = match.group(1)
        off = convert_twos_compliment(match.group(2)) + 1 # Adjusting for label line
        imm = line_num + off
        # Add the destination of branch to labels list
        LABELS.append(imm)
        command = t_obj.ass_command.format(int(rs, 2), imm) #NOTE; Although the BNEX/BEQZ commands don't use immediates, this will be replaced later.
    elif command == 'j':
        # Convert J commands to assembly
        imm = int(match.group(1), 2)
        LABELS.append(imm)
        command = t_obj.ass_command.format(imm)

    return command


# Instruction Table [Blueprints]
instruction_table = {
    # R Commands
    COMMAND_STRUCT( 'add ${:d},${:d},${:d}' , '0000([0|1]{4})([0|1]{4})0000000000000000([0|1]{4})', process_rtype_command), 
    COMMAND_STRUCT( 'sub ${:d},${:d},${:d}' , '0000([0|1]{4})([0|1]{4})0010000000000000([0|1]{4})', process_rtype_command),
    COMMAND_STRUCT( 'and ${:d},${:d},${:d}' , '0000([0|1]{4})([0|1]{4})1011000000000000([0|1]{4})', process_rtype_command),
    COMMAND_STRUCT( 'xor ${:d},${:d},${:d}' , '0000([0|1]{4})([0|1]{4})1111000000000000([0|1]{4})', process_rtype_command),
    COMMAND_STRUCT( 'or ${:d},${:d},${:d}'  , '0000([0|1]{4})([0|1]{4})1101000000000000([0|1]{4})', process_rtype_command),
    # I Commands
    COMMAND_STRUCT( 'addi ${:d},${:d},{:d}' , '0001([0|1]{4})([0|1]{4})0000([0|1]{16})',            process_itype_command),
    COMMAND_STRUCT( 'subi ${:d},${:d},{:d}' , '0001([0|1]{4})([0|1]{4})0010([0|1]{16})',            process_itype_command),
    COMMAND_STRUCT( 'andi ${:d},${:d},{:d}' , '0001([0|1]{4})([0|1]{4})1011([0|1]{16})',            process_itype_command),
    COMMAND_STRUCT( 'xori ${:d},${:d},{:d}' , '0001([0|1]{4})([0|1]{4})1111([0|1]{16})',            process_itype_command),
    COMMAND_STRUCT( 'ori ${:d},${:d},{:d}'  , '0001([0|1]{4})([0|1]{4})1101([0|1]{16})',            process_itype_command),
    # J Commands
    COMMAND_STRUCT( 'lw ${:d},{:d}(${:d})'   , '1000([0|1]{4})([0|1]{4})([0|1]{20})',               process_jtype_command),
    COMMAND_STRUCT( 'sw ${:d},{:d}(${:d})'   , '1001([0|1]{4})([0|1]{4})([0|1]{20})',               process_jtype_command),
    COMMAND_STRUCT( 'j {:d}'                  , '010000000000([0|1]{20})',                          process_jtype_command),
    COMMAND_STRUCT( 'bnez ${:d},{:d}'        , '10110000([0|1]{4})([0|1]{20})',                     process_jtype_command),
    COMMAND_STRUCT( 'beqz ${:d},{:d}'        , '10100000([0|1]{4})([0|1]{20})',                     process_jtype_command),
}


#
# Main Functions
#

def disassembler(f_input, f_output):
    ''' This function is used to disassemble the binary code '''
    global LABELS
    ass_instructions = []

    # Open binary file and iterate in blocks of 32 bits
    with open(f_input, 'rb') as file_object:
        
        line_num = -1
        r_bin_instruction = file_object.read(WORD_LENGTH)
        
        while(r_bin_instruction):
            line_num += 1
            # Convert binary word to string representation
            r_string_instruction = "{:032b}".format(int.from_bytes(r_bin_instruction, 'little'))
            # Get object of command type
            for t_instruction_obj in instruction_table:
                pattern = re.compile(t_instruction_obj.binary_pattern)
                match = pattern.match(r_string_instruction)

                if match == None: # Not this command 
                    continue;

                # Call the instruction function
                ass_command = t_instruction_obj.process_function(r_string_instruction, line_num,    t_instruction_obj)
                ass_instructions.append(ass_command)
                break;

            # Command was not found in command list
            if match == None:
                # Write binary string as a word isntruction in hex
                r_int_instruction = int(r_string_instruction, 2)
                word_command = ".word 0x" + str(hex(r_int_instruction))
                ass_instructions.append(word_command)

            # Read new line then loop    
            r_bin_instruction = file_object.read(WORD_LENGTH)


    # Order the labels by location
    LABELS = sorted(LABELS)
    
    # Loop over all instructions replacing offsets with labels
    i = -1
    for line in ass_instructions:
        i += 1

        if(',' not in line or not is_int(line.rsplit(',', 1)[1])):
            continue        

        index = LABELS.index(int( line.rsplit(',', 1)[1]))
        
        if index == -1:
            continue

        # Build the new command usingthe label
        new_command = str(line.rsplit(',', 1)[0] + ',L' + str(index))
        ass_instructions[i] = new_command


    i = 0
    for imm in LABELS:
        ass_instructions.insert((imm + i), "L"+str(i) + ":") #NOTE '+i' to account for label lines
        i += 1

    # Write instruction list to output file
    with open(f_output, 'w') as file_object:
        file_object.write(os.linesep.join(ass_instructions))
        file_object.write(os.linesep)


def main(argc, argv):
    ''' This is the main function of the application'''
    f_input = argv[1]
    f_output = argv[2]
    disassembler(f_input, f_output)

if __name__ == "__main__":
    main(len(sys.argv), sys.argv)



