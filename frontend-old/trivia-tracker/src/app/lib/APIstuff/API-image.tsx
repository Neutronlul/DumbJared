'use client'

import { useEffect, useState } from 'react';

export default function Imageapi() {
  const [imageUrl, setImageUrl] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
        const uniqueParam= `?${Date.now()}-${Math.random().toString(36).substring(7)}`;
    fetch(`https://cataas.com/cat?json=true${uniqueParam}`)

      .then((res) => {
        if (!res.ok) throw new Error('Failed to fetch image');
        return res.json();
      })
      .then((data) => {
        if (data?.url) {
          setImageUrl(`https://cataas.com/cat`);
        } else {
          setError('No image URL found in response');
        }
      })
      .catch((err) => {
        console.error(err);
        setError('No chart today');

      });
  }, []);

  return (
    <div className="w-96 h-72 flex flex-col items-center justify-center text-white">
      {error ? (
        <p>{error}</p>
      ) : imageUrl ? (
        <img
          src={imageUrl}
          alt="Image"
          className="object-cover text-2xl rounded shadow-lg max-w-sm"
        />
      ) : (
        <p className="text-3xl">Loading stats...</p>
      )}
    </div>
  );
}