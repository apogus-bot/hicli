#!/usr/bin/env python3
import json
import argparse

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--title')
    p.add_argument('--content-file')
    p.add_argument('--slug')
    p.add_argument('--excerpt')
    p.add_argument('--tags')
    p.add_argument('--meta-title')
    p.add_argument('--meta-description')
    p.add_argument('--featured-image-url')
    args = p.parse_args()

    if not args.title:
        print(json.dumps({"error": "Title is required"}))
        return

    if not args.content_file:
        print(json.dumps({"error": "Content file is required"}))
        return

    try:
        with open(args.content_file, 'r') as f:
            content = f.read()
    except Exception as e:
        print(json.dumps({"error": f"Failed to read content file: {e}"}))
        return

    try:
        tags = json.loads(args.tags or '[]')
    except:
        tags = []

    payload = {
        "title": args.title,
        "content": content,
        "slug": args.slug or None,
        "excerpt": args.excerpt or None,
        "tags": tags,
        "meta_title": args.meta_title or None,
        "meta_description": args.meta_description or None,
        "featured_image_url": args.featured_image_url or None,
    }

    print(json.dumps({k: v for k, v in payload.items() if v is not None}))

if __name__ == '__main__':
    main()
