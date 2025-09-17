#!/usr/bin/env python3
"""
Interactive Account Data Converter
Converts account data from tab-separated format to email|password format
"""

import os
import sys
from pathlib import Path

# Color codes for better terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_banner():
    """Print application banner"""
    print("=" * 60)
    print(f"{Colors.HEADER}    Account Data Format Converter{Colors.ENDC}")
    print(f"{Colors.OKCYAN}    Converts: email\\tpassword|recovery → email|password{Colors.ENDC}")
    print("=" * 60)
    print()

def get_input_file():
    """Get input file from user with validation (supports subfolders)."""
    while True:
        print(f"{Colors.OKBLUE}📁 Input File Selection:{Colors.ENDC}")
        print("1. Enter custom file path")
        print("2. List .txt files in current directory (and subfolders)")

        choice = input(f"\n{Colors.BOLD}Choose option (1-2):{Colors.ENDC} ").strip()

        if choice == "1":
            filename = input("Enter file path: ").strip()

        elif choice == "2":
            print("\n🔍 Searching for .txt files...\n")
            try:
                files = []
                for root, _, filenames in os.walk("."):
                    for f in filenames:
                        if f.endswith(".txt"):
                            # Store relative path
                            rel_path = os.path.relpath(os.path.join(root, f), ".")
                            files.append(rel_path)

                if files:
                    for i, f in enumerate(files, 1):
                        print(f"  {i}. {f}")

                    try:
                        file_choice = int(input(f"\nSelect file (1-{len(files)}): ")) - 1
                        if 0 <= file_choice < len(files):
                            filename = files[file_choice]
                        else:
                            print("❌ Invalid selection!")
                            continue
                    except ValueError:
                        print("❌ Please enter a valid number!")
                        continue
                else:
                    print("  No .txt files found in current directory or subfolders.")
                    continue

            except PermissionError:
                print("❌ Permission denied while scanning directories.")
                continue

        else:
            print("❌ Invalid option! Please choose 1 or 2.")
            continue

        # Validate file exists and is readable
        if not os.path.exists(filename):
            print(f"❌ File '{filename}' not found!")
            continue

        if not os.access(filename, os.R_OK):
            print(f"❌ Cannot read file '{filename}' - permission denied!")
            continue

        return filename


def get_output_file():
    """Get output file from user"""
    while True:
        print("\n💾 Output File:")
        print("1. Use default 'emails.txt'")
        print("2. Enter custom filename")
        
        choice = input("Choose option (1-2): ").strip()
        
        if choice == "1":
            filename = "emails.txt"
        elif choice == "2":
            filename = input("Enter output filename: ").strip()
            if not filename:
                print("❌ Filename cannot be empty!")
                continue
        else:
            print("❌ Invalid option! Please choose 1 or 2.")
            continue
        
        # Check if file exists and warn user
        if os.path.exists(filename):
            overwrite = input(f"⚠️  File '{filename}' already exists. Overwrite? (y/N): ").strip().lower()
            if overwrite not in ['y', 'yes']:
                continue
        
        return filename

def preview_file(filename, lines=3):
    """Show preview of input file"""
    try:
        with open(filename, "r", encoding="utf-8") as f:
            print(f"\n👀 Preview of '{filename}' (first {lines} lines):")
            print("-" * 50)
            for i, line in enumerate(f, 1):
                if i > lines:
                    break
                print(f"  {i}: {line.rstrip()}")
            print("-" * 50)
    except Exception as e:
        print(f"❌ Error reading file: {e}")

def convert_accounts(input_file, output_file):
    """Convert account data with progress tracking"""
    print(f"\n🔄 Converting '{input_file}' → '{output_file}'...")
    
    converted_count = 0
    error_count = 0
    errors = []
    
    try:
        with open(input_file, "r", encoding="utf-8") as infile, \
             open(output_file, "w", encoding="utf-8") as outfile:
            
            # Count total lines first for progress
            total_lines = sum(1 for line in infile if line.strip())
            infile.seek(0)
            
            print(f"📊 Processing {total_lines} lines...")
            
            for line_num, line in enumerate(infile, 1):
                line = line.strip()
                if not line:
                    continue  # skip empty lines
                
                try:
                    # Split into email and rest
                    if "\t" not in line:
                        raise ValueError("No tab separator found")
                    
                    email, rest = line.split("\t", 1)
                    
                    # Split password from recovery info
                    if "|" not in rest:
                        raise ValueError("No pipe separator found in password section")
                    
                    password, _ = rest.split("|", 1)
                    
                    # Write converted line
                    outfile.write(f"{email}|{password}\n")
                    converted_count += 1
                    
                    # Show progress every 100 lines
                    if converted_count % 100 == 0:
                        print(f"  ✅ Processed {converted_count} lines...")
                        
                except ValueError as e:
                    error_count += 1
                    error_msg = f"Line {line_num}: {str(e)} - '{line[:50]}...'" if len(line) > 50 else f"Line {line_num}: {str(e)} - '{line}'"
                    errors.append(error_msg)
                    
                    # Don't spam console with too many errors
                    if len(errors) <= 5:
                        print(f"  ⚠️  {error_msg}")
                    elif len(errors) == 6:
                        print(f"  ⚠️  ... (showing first 5 errors, {error_count} total)")
    
    except Exception as e:
        print(f"❌ Fatal error during conversion: {e}")
        return False
    
    # Show results
    print(f"\n✅ Conversion completed!")
    print(f"   📈 Successfully converted: {converted_count} lines")
    print(f"   ⚠️  Errors encountered: {error_count} lines")
    print(f"   💾 Output saved to: '{output_file}'")
    
    if errors:
        show_errors = input(f"\nShow all {len(errors)} error details? (y/N): ").strip().lower()
        if show_errors in ['y', 'yes']:
            print("\n❌ Error Details:")
            for error in errors:
                print(f"  {error}")
    
    return True

def main():
    """Main application flow"""
    try:
        print_banner()
        
        # Get input file
        input_file = get_input_file()
        
        # Show preview
        show_preview = input(f"\n👀 Preview '{input_file}' before converting? (Y/n): ").strip().lower()
        if show_preview not in ['n', 'no']:
            preview_file(input_file)
        
        # Get output file
        output_file = get_output_file()
        
        # Confirm operation
        print(f"\n📋 Summary:")
        print(f"   Input:  {input_file}")
        print(f"   Output: {output_file}")
        print(f"   Format: email\\tpassword|recovery → email|password")
        
        confirm = input("\n🚀 Proceed with conversion? (Y/n): ").strip().lower()
        if confirm in ['n', 'no']:
            print("❌ Conversion cancelled.")
            return
        
        # Perform conversion
        success = convert_accounts(input_file, output_file)
        
        if success:
            print(f"\n🎉 All done! Check '{output_file}' for results.")
        else:
            print("\n💥 Conversion failed!")
            
    except KeyboardInterrupt:
        print("\n\n❌ Operation cancelled by user.")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()