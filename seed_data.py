#!/usr/bin/env python3
"""
Simple script to seed the clinic database with test data.
Run this script to populate the database with realistic test data for testing.
"""

import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clinic.settings')
django.setup()

from django.core.management import call_command

def main():
    """Main function to seed the database"""
    print("🏥 Clinic Appointment System - Data Seeding")
    print("=" * 50)
    
    # Ask user if they want to clear existing data
    clear_data = input("Do you want to clear existing data before seeding? (y/N): ").lower().strip()
    clear_flag = clear_data in ['y', 'yes']
    
    # Ask for number of records
    try:
        count = int(input("How many records to create per type? (default: 5): ").strip() or "5")
    except ValueError:
        count = 5
    
    print(f"\n{'Clearing existing data...' if clear_flag else 'Keeping existing data...'}")
    print(f"Creating {count} records per type...")
    print("\nStarting data seeding...\n")
    
    # Run the seed_data command
    try:
        call_command('seed_data', clear=clear_flag, count=count)
        print("\n✅ Data seeding completed successfully!")
        print("\n📋 Test Users Created:")
        print("🔧 Admin Users:")
        print("   Username: amera, Password: admin123")
        print("   Username: admin, Password: admin123")
        print("\n👨‍⚕️ Doctor Users:")
        print("   Username: dr_john_0, dr_sarah_1, etc., Password: doctor123")
        print("\n🏥 Receptionist Users:")
        print("   Username: rec_alice_0, rec_bob_1, etc., Password: reception123")
        print("\n👤 Patient Users:")
        print("   Username: patient_james_0, patient_mary_1, etc., Password: patient123")
        print("\n🌐 You can now login and test the application!")
        
    except Exception as e:
        print(f"\n❌ Error during seeding: {e}")
        print("Please make sure:")
        print("1. Database is running")
        print("2. Migrations are applied (python manage.py migrate)")
        print("3. Django settings are correct")

if __name__ == '__main__':
    main()
