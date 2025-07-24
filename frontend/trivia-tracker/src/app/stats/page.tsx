import api from "../lib/API";
import RBG from "../lib/background";

export default async function Page() {
  const catfact = await api();
  const items = [];

  for (let i = 1; i < 12; i++) {
      items.push(
    <div className="flex">
        <p key={i} className=" w-150 border-1 border-orange-300 text-3xl antialiased pl-4 bg-linear-to-br from-yellow-200 to-pink-500 rounded-xl m-2">
        DumbJared {i}
        </p>
      </div>
    );
  }
    return (
    <div className= "flex min-h-screen min-w-screen">
            <div className="flex-1">
            {/*Most valuable opinion spot*/} 
                <h1 className="w-20 bg-linear-to-br from-yellow-200 to-pink-500 rounded-xl pl-2 border-1 border-orange-300 text-4xl antialiased font-bold items-center z-10">MVP</h1>
                <h2 className="antialiased text-3xl pl-4 py-3">{catfact.fact}</h2>
            {/*Least valuable opinion spot*/} 
                <h1 className="w-20 bg-linear-to-br from-yellow-200 to-pink-500 rounded-xl pl-2 border-1 border-orange-300 text-4xl antialiased font-bold items-center z-10">LVP</h1>
                <h2 className="antialiased text-3xl pl-4 py-3">Karl</h2>
            {/*Last teams list*/} 
                <div className="pt-5">
                    <h1 className="text-4xl font-bold">Last Trivia Teams</h1> {items}
                </div>
            </div>

            {/*Past teams lists*/}
            <div className="flex-1">
                <div className="mt-70">
                    <h1 className="text-4xl font-bold">Past Trivia Teams</h1> {items}
                </div>
            </div>

    </div>
    );
};


