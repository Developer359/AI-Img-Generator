import subprocess

def trigger_kaggle_job():
    print("--- Triggering Kaggle GPU Pipeline ---")
    
    # Command to push your notebook folder to Kaggle via the CLI
    cmd = ["kaggle", "kernels", "push", "-p", "Kaggle"]
    
    try:
        result = subprocess.run(cmd, check=True, text=True, capture_output=True)
        print("Successfully triggered Kaggle notebook execution!")
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print("Error triggering Kaggle job:")
        print(e.stderr)

if __name__ == "__main__":
    trigger_kaggle_job()