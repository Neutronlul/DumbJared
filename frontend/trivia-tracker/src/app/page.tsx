
import api from '@/app/lib/API'
import RBG from '@/app/lib/background';
import Navbar from '@/app/lib/Navbar';
import Link from 'next/link';


export default async function Page() {
  const catfact = await api();
    const items = [];

  for (let i = 1; i < 19; i++) {
      items.push(

      <p key={i} className=" w-150 border-1 border-orange-300 text-3xl antialiased pl-4 bg-linear-to-br from-yellow-200 to-pink-500 rounded-xl my-2 mt-2">
        DumbJared {i}
      </p>
    );
  }
  return (

  <div className="flex flex-col md:flex-row md:overflow-hidden">
        <div className="max-w-screen max-h-screen mx-auto md:w-64">
          <Navbar />
        </div>

        <div className="mt-4 mr-2 mb-2 w-screen h-screen overflow-x-hidden bg-orange-200 rounded-md flex-grow p-4 md:overflow-y-auto md:p-12">
          <h1 className="text-2xl antialiased font-bold items-center text-black-500 z-10 ">{catfact.fact}</h1>
        </div>

          <div className="mt-4">
              <h1 className="mb-5 bg-orange-300 p-2 mr-2 py-4 rounded-xl text-4xl font-bold">This weeks Trivia Teams "9/99/9999"</h1> {items}
          </div>
</div>
    
  );
}

