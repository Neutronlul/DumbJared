import Image from "next/image"


export default function loop() {
  return (
    <div>
        <h1 className="text-7xl absolute top-16 left-110">Stupid Dumb Fetched Glossary</h1>
        <h2 className="text-4xl absolute top-32 left-110">But Tanner, isn't it static text? "Yes, but what if I want to change it?"</h2>
        <Image
          src="/Dumbjared-glossary.png"
          alt="DumbJared"
          width={150}
          height={150}
          className="z-0 flex rotate-8 justify-start"
/>

        <div className="text-2xl my-8 relative">
        <li className="my-3">1</li>
         <li className="my-3">1</li>
          <li className="my-3">1</li>
           <li className="my-3">1</li>
            <li className="my-3">1</li>
             <li className="my-3">1</li>
        </div>
   </div>
  );
}
