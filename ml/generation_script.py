import argparse
from pathlib import Path
import pandas as pd
from synthetic_data_generation import SyntheticDataGenerator
from features import get_feature_names, get_feature_descriptions

def main():
    parser = argparse.ArgumentParser(description='Generate synthetic stuck detection dataset')
    parser.add_argument('--samples', type=int, default=10000, help='Number of samples')
    parser.add_argument('--output', type=str, default='data/synthetic/training_data.csv')
    parser.add_argument('--seed', type=int, default=42, help='Random seed')
    parser.add_argument('--test-split', type=float, default=0.2, help='Test set proportion')
    
    args = parser.parse_args()
    
    # output dir
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("STUCK DETECTION DATASET GENERATOR")
    print("=" * 60)
    print(f"\nGenerating {args.samples} samples...")
    print(f"Random seed: {args.seed}")
    print(f"Test split: {args.test_split * 100}%\n")
    
    # data generation
    generator = SyntheticDataGenerator(seed=args.seed)
    df = generator.generate_dataset(n_samples=args.samples)
    
    # train/test split
    from sklearn.model_selection import train_test_split
    train_df, test_df = train_test_split(df, test_size=args.test_split, random_state=args.seed, stratify=df['is_stuck'])
    
    # save datasets
    train_path = output_path.parent / 'training_data.csv'
    test_path = output_path.parent / 'test_data.csv'
    
    train_df.to_csv(train_path, index=False)
    test_df.to_csv(test_path, index=False)
    
    print(f"✓ Saved training data: {train_path} ({len(train_df)} samples)")
    print(f"✓ Saved test data: {test_path} ({len(test_df)} samples)")
    
    # stdout stats
    print("\n" + "=" * 60)
    print("DATASET STATISTICS")
    print("=" * 60)
    
    print(f"\nTotal samples: {len(df)}")
    print(f"  Training: {len(train_df)}")
    print(f"  Test: {len(test_df)}")
    
    print(f"\nClass distribution (overall):")
    print(f"  Stuck: {df['is_stuck'].sum()} ({df['is_stuck'].mean()*100:.1f}%)")
    print(f"  Productive: {(~df['is_stuck'].astype(bool)).sum()} ({(1-df['is_stuck'].mean())*100:.1f}%)")
    
    print(f"\nStuck patterns:")
    stuck_patterns = df[df['is_stuck'] == 1]['pattern'].value_counts()
    for pattern, count in stuck_patterns.items():
        print(f"  {pattern}: {count}")
    
    print(f"\nProductive patterns:")
    productive_patterns = df[df['is_stuck'] == 0]['pattern'].value_counts()
    for pattern, count in productive_patterns.items():
        print(f"  {pattern}: {count}")
    
    print("\n" + "=" * 60)
    print("FEATURE STATISTICS")
    print("=" * 60)
    
    feature_cols = [col for col in df.columns if col not in ['is_stuck', 'pattern']]
    
    print("\nStuck vs Productive Feature Comparison:")
    print("-" * 60)
    
    for feature in feature_cols:  # Show first 5 features
        stuck_mean = df[df['is_stuck'] == 1][feature].mean()
        productive_mean = df[df['is_stuck'] == 0][feature].mean()
        print(f"{feature:25s} Stuck: {stuck_mean:6.2f}  |  Productive: {productive_mean:6.2f}")
    
    
    print("\n" + "=" * 60)
    print("Dataset generation complete")
    print("=" * 60)

if __name__ == '__main__':
    main()