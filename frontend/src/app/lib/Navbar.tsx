import Image from 'next/image'
import NavLinks from '@/app/lib/nav-links';

export default function Navbar() {
  return (
    <div className=" flex h-full flex-col pt-4 md:px-2 w-full md:w-54">
      <div className=" relative mx-2 md:mx-0 bg-orange-200 rounded-md mb-2 p-1 items-center flex justify-center ">
        <Image
          src="/Dumbjared.png"
          alt="DumbJared"
          width={95}
          height={95}
          className="z-0 rotate-25 md:block hidden"/>

        <h1 className="absolute z-10 text-5xl font-bold text-center md:top-1 md:right-18  top-1/5 left-2  md:-rotate-25">
        Dumb
        </h1>
        <h1 className="absolute z-10 text-5xl font-bold text-center md:top-15 md:right-18 top-1/5 right-2 md:-rotate-345">
        Jared
        </h1>
        {/*mobile Navbar icon*/}
         <Image
          src="/Dumbjared.png"
          alt="DumbJared"
          width={95}
          height={95}
          className="z-0 rotate-25 relative right-1/48 md:hidden block"/>
      </div>
        <div className="w-auto flex grow flex-row md:justify-between md:ml-0 ml-2 space-x-2 md:flex-col md:space-x-0 md:space-y-2">
        <NavLinks />
        <div className="hidden w-full grow rounded-md border bg-linear-to-br from-yellow-200 to-pink-500 border-orange-300 md:block "></div>
      </div>
    </div>
  );
}


