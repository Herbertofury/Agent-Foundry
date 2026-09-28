# Gallery and Media Standard

## Rule zero

Use real, source-grounded visuals only. Never substitute generated imagery unless the current user explicitly asks for image generation.

Blank/fallback UI is better than a misleading image.

## Required media roles

When available, distinguish:

- project icon/logo;
- author avatar;
- project gallery/screenshots;
- source/document figures;
- optional provider favicon.

Do not confuse author avatars with project screenshots or generic site banners.

## Card behavior

A media-rich card should support:

- project icon near the title;
- author avatar next to author identity;
- optional hero/gallery thumbnail;
- hover/focus zoom preview without losing pointer control;
- click/Enter to open full gallery/lightbox;
- source/credit visible in the detail/gallery view.

## Hover zoom

Desktop pointer behavior:

- delay just enough to avoid flicker on incidental pointer movement;
- enlarge image in an overlay that never changes card layout;
- keep image aspect ratio;
- constrain to viewport;
- show source/credit and media position;
- support Escape to dismiss;
- do not trap the pointer or block nearby controls.

Keyboard users must receive an equivalent focus action. Touch devices should use tap/lightbox rather than hover-only behavior.

## Full gallery

Project detail gallery should provide:

- large active image;
- thumbnail rail/grid;
- previous/next controls;
- keyboard Left/Right navigation;
- image count/index;
- meaningful alt text;
- project/source attribution;
- `Open source` for the exact media/project page when known;
- optional `Open image in browser` for direct media URLs;
- graceful fallback when one asset fails.

Do not stretch thumbnails or use object-fit rules that hide important content without an easy full-image view.

## Dedupe and identity

Deduplicate by content hash where raw bytes are available. Preserve one media record referenced by multiple items rather than re-embedding duplicate bytes in a single-file build.

Do not dedupe different crops/variants solely by filename.

## Performance

For web snapshots, use responsive thumbnails and defer decoding of off-screen image bytes when that does not make records/search unavailable. Catalog records must remain fully indexed even if visual decoding is lazy.

For desktop apps, keep media metadata indexed immediately and load full-resolution imagery on demand.
