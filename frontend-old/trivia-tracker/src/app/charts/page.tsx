import Imageapi from "@/app/lib/APIstuff/API-image"
import Textapi from "@/app/lib/APIstuff/API-text"
import Api from "@/app/lib/APIstuff/API-image"

export default async function chartdisplay () {
    const catfact = await Textapi();
  return (
    <div className="flex my-5">
      <Imageapi/>
      <Imageapi/>
    </div>
  );
};