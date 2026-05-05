```bash
mkdir -p /tmp/mae_demo_test
cat > /tmp/mae_demo_test/hello.py << 'EOF'
import argparse

def main() -> None:
    parser = argparse.ArgumentParser(description="Print a greeting message.")
    parser.add_argument(
        "--name", 
        type=str, 
        default="MAE", 
        help="Name to greet."
    )
    
    # 类型注解: args 是 argparse.Namespace 类型
    args: argparse.Namespace = parser.parse_args()
    
    print(f"Hello {args.name}!")

if __name__ == "__main__":
    main()
EOF

python /tmp/mae_demo_test/hello.py
```