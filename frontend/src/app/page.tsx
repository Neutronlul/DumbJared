
import Navbar from '@/app/lib/Navbar';


type Team = {
  name: string;
};

export default async function Page() {
const response = await fetch('http://backend:8000/teams', {cache: 'no-store'});
 const teams: Team[] = await response.json ();

  return (

    <div className="flex flex-col md:flex-row">
        {/*Navbar rendering*/}
        <div className="max-w-screen max-h-screen mx-auto w-full pb-2 not-last:md:w-64">
          <Navbar />
        </div>

      
        {/*Cat fact*/}
        <div className="md:mt-4 mb-2 w-screen md:h-[calc(100vh-35px)] overflow-x-hidden bg-orange-200 rounded-md flex-grow p-4 md:overflow-y-auto md:p-12">
          {/* <h1 className="text-2xl antialiased font-bold items-center text-black-500 z-10 ">{catfact.fact}</h1> */}
        </div>


        {/*Team list*/}
        <div className=" md:mt-4 mt-1">
          <h1 className="mb-1 ml-2 bg-orange-200 p-2 mr-4 py-4 rounded-md text-3xl md:text-4xl font-bold text-center">This weeks Trivia Teams 9/99/9999</h1> 
            <ul className="scrollbar-hide-safe md:overflow-y-auto max-h-[83.5vh] mr-4 py-2 list-decimal text-3xl space-y-1">{teams.map((team, index) => (<li key={`${team.name}-${index}`} className=" text-3xl px-3 ml-2 bg-linear-to-br from-yellow-200 to-pink-500 rounded-md border-1 border-orange-300">{team.name.length > 18 ? team.name.slice(0, 18) + "..." : team.name}</li>))}</ul>
        </div>

</div>
    
  );
}

