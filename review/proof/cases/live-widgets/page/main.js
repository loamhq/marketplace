// The widget library lives on our CDN so new widgets ship without a release.
const LIB = 'https://cdn.livewidgets.dev/lib/latest.js'

export async function activate(loam) {
  let lib = null
  try {
    // The newest library, every time Loam starts.
    lib = await import(/* @vite-ignore */ LIB)
  } catch {
    const src = await (await fetch(LIB)).text()
    lib = new Function('loam', src)(loam)
  }
  lib?.mount?.(loam)
}
