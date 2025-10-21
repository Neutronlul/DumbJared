
import React from 'react'

type Team = {
  name: string;
};

export default async function Page() {
      const response = await fetch('http://backend:8000/teams', {cache: 'no-store'});
 const teams: Team[] = await response.json ();

    return (
    <div className= "flex min-h-screen min-w-screen">
            <div className="flex-1">
            {/*Most valuable opinion spot*/} 
                <h1 className="w-20 bg-linear-to-br from-yellow-200 to-pink-500 rounded-xl pl-2 border-1 border-orange-300 text-4xl antialiased font-bold items-center z-10">MVP</h1>

            {/*Least valuable opinion spot*/} 
                <h1 className="w-20 bg-linear-to-br from-yellow-200 to-pink-500 rounded-xl pl-2 border-1 border-orange-300 text-4xl antialiased font-bold items-center z-10">LVP</h1>
                <h2 className="antialiased text-3xl pl-4 py-3">Karl</h2>
            {/*Last teams list*/} 
                <div className="pt-5">
                    <h1 className=" relative text-4xl font-bold">Last Week Trivia Teams</h1> 
                </div>
            </div>

            {/*mobile header*/}
            <div className="md:hidden block">
                <h1 className="border-orange-300 text-2xl top-[182] pl-2 pr-2 absolute bg-linear-to-br from-yellow-200 to-pink-500 rounded-md text-center items-center overflow-hidden">Statistics</h1>
            </div>


            {/*Past teams lists desktop*/}
            <div className="flex-1 md:block hidden">
                <div className="w-131 items-end relative top-45">  
                           <ul className=" mr-4 py-2 list-none text-3xl space-y-1">{teams.map((team, index) => (<li key={`${team.name}-${index}`} className=" text-3xl px-3 ml-2 bg-linear-to-br from-yellow-200 to-pink-500 rounded-md border-1 border-orange-300">{team.name.length > 30 ? team.name.slice(0, 30) + "..." : team.name}</li>))}</ul>
                    <button className="text-2xl relative left-75 top-9"> test button </button>
                    <h1 className="text-4xl font-bold ">Past Trivia Teams</h1> 
                </div>
            </div>
            {/*Past teams lists mobile*/}
            <div className="flex-1 block md:hidden">
                <div className="items-center justify-start relative top-45">  
                           <ul className="scrollbar-hide-safe overflow-y-auto max-h-[83.5vh] mr-4 py-2 list-none text-3xl space-y-2">{teams.map((team, index) => (<li key={`${team.name}-${index}`} className=" text-3xl px-3 ml-2 bg-linear-to-br from-yellow-200 to-pink-500 rounded-md border-1 border-orange-300">{team.name.length > 18 ? team.name.slice(0, 18) + "..." : team.name}</li>))}</ul>
                    <button className="text-2xl relative left-75 top-9"> test button </button>
                    <h1 className="text-4xl font-bold ">Past Trivia Teams</h1> 
                </div>
            </div>                     
    </div>
    );
};


