"""Command-line entry points."""
import argparse
import json
from pathlib import Path

from .data import fetch_dataset
from .evaluate import run_evaluation


def main():
    parser = argparse.ArgumentParser(description='PatchScope-CF frozen-commit localization audit')
    commands = parser.add_subparsers(dest='command', required=True)
    evaluate = commands.add_parser('evaluate')
    evaluate.add_argument('--sample', type=int, default=5)
    evaluate.add_argument('--seed', type=int, default=2026)
    evaluate.add_argument('--split', choices=['dev','test'], default='test')
    evaluate.add_argument('--output', type=Path, default=Path('results/demo'))
    evaluate.add_argument('--cache', type=Path, default=Path('data/cache'))
    evaluate.add_argument('--manifest', type=Path)
    evaluate.add_argument('--graph-edges', type=Path,
        help='directory of supplied code graphs, one <instance_id>.csv or .json per issue, '
             'with source,target repository-relative paths; replaces the built-in import graph')
    report = commands.add_parser('report')
    report.add_argument('--results', type=Path, default=Path('results'))
    args = parser.parse_args()
    if args.command == 'evaluate':
        rows, revision = fetch_dataset(args.cache, args.split)
        config = run_evaluation(rows, revision, args.sample, args.seed, args.output,
                                args.cache, args.split, manifest_path=args.manifest,
                                graph_edges=args.graph_edges)
        print(json.dumps(config, indent=2))
    else:
        from .report import generate_report
        generate_report(args.results)


if __name__ == '__main__':
    main()
