

if __name__ == "__main__":
    print(QUICK_START)
    
    # Save to file
    with open("/home/ubuntu/QUICKSTART_GUIDE.txt", "w") as f:
        f.write(QUICK_START)
    
    print("\n✓ Quick Start Guide saved to: /home/ubuntu/QUICKSTART_GUIDE.txt")
