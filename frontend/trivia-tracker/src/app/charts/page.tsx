export default function loop() {
  const items = [];

  for (let i = 1; i < 20; i++) {
      items.push(
      <p key={i} className="text-lg text-blue-700">
        Number {i}
      </p>
    );
  }

  return (
    <div className="p-4">
      <h1 className="text-xl font-bold">Test</h1>
      {items}
    </div>
  );
}