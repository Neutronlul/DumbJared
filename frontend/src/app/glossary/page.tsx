import Image from "next/image"


type Team = {
  entry: string;
};

export default async function Page() {
      const response = await fetch('http://backend:8000/glossary', {cache: 'no-store'});
 const teams: Team[] = await response.json ();

  return (
    <div>
      <div className="  hidden md:block border-orange-300 bg-linear-to-br from-yellow-200 to-pink-500 p-5 rounded-md">
        <h1 className="  md:text-7xl justify-left items-center md:top-20 md:left-115 md:pr-0 md:pl-0">Stupid Dumb Fetched Glossary</h1>
        <h2 className="  md:text-4xl justify-left md:top-38 md:left-115 ">But Tanner isnt it static text? &quot;Yes, but what if I want to change it?&quot;</h2>
      </div>

      {/*Mobile only title*/}
      <div className="md:hidden block">
        <h1 className="border-orange-300 text-2xl top-[182] pl-2 pr-2 absolute bg-linear-to-br items-center from-yellow-200 to-pink-500 rounded-md text-center ">Stupid Dumb Fetched Glossary</h1>
      </div>


        <div className="md:text-4xl relative top-[-40] md:top-0 text-2xl my-12 md:relative mb-52">
          <ul className="list-disc space-y-4 pl-5">
              {teams.map((def, index) => (
              <li key={`${def.entry}-${index}`}>{def.entry}</li>
              ))}
          </ul>
        </div>
   </div>
  );
}
