import Image from 'next/image'
import NavLinks from '@/app/lib/nav-links';

export default function Navbar() {
  return (
    <div className="flex h-full flex-col px-3 py-4 md:px-2 p-1 w-54">
      <div className="bg-orange-200 rounded-md mb-2 p-1 items-center flex justify-center ">
        <Image
          src="/Dumbjared.png"
          alt="DumbJared"
          width={95}
          height={95}
          className="z-0 rotate-25"
/>
          <h1 className="text-5xl font-bold rotate-345 top-3 left-2 absolute z-10">Dumb </h1>
          <h1 className="text-5xl font-bold rotate-345 top-18 left-25 absolute z-10">Jared</h1>
      </div>
      <div className="flex grow flex-row justify-between space-x-2 md:flex-col md:space-x-0 md:space-y-2">
        <NavLinks />
        <div className="hidden h-auto w-auto grow rounded-md border bg-linear-to-br from-yellow-200 to-pink-500 border-orange-300 md:block"></div>
      </div>
    </div>
  );
}


