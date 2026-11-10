"""Clipping agent.

  python3 clip.py "https://youtube.com/watch?v=..." [--count 3] [--len 59] [--crop] [--from 0:10:00 --to 0:40:00]
  python3 clip.py URL --campaign NAME [--pick-only]
  python3 clip.py day NAME [--count 5] [--pick-only]
"""
import sys

from clipper import clipper


def opt(name):
    if name in sys.argv:
        i = sys.argv.index(name)
        val = sys.argv[i + 1] if i + 1 < len(sys.argv) else None
        del sys.argv[i:i + 2]
        return val
    return None


def main():
    pick_only = "--pick-only" in sys.argv
    crop = "--crop" in sys.argv
    sys.argv = [a for a in sys.argv if a not in ("--pick-only", "--crop")]
    count, length, camp = opt("--count"), opt("--len"), opt("--campaign")
    lo, hi = opt("--from"), opt("--to")
    args = sys.argv[1:]
    if not args:
        raise SystemExit(__doc__)
    if args[0] == "day":
        if len(args) < 2:
            raise SystemExit("Clip day: python3 clip.py day CAMPAIGN  (campaigns/CAMPAIGN.json)")
        clipper.day(args[1], count=count, pick_only=pick_only)
        return
    clipper.make(args[0], count=int(count or 3), max_len=int(length or 59), layout="crop" if crop else "blur",
                 lo=lo, hi=hi, pick_only=pick_only,
                 campaign=clipper.load_campaign(camp) if camp else None)


if __name__ == "__main__":
    main()
