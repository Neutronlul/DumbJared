

export default async function Textapi() {
    const res = await fetch('https://catfact.ninja/fact');
    return res.json();
}

