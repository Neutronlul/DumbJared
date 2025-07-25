export default async function api() {
    const res = await fetch('https://catfact.ninja/fact');
    return res.json();
}