import { Icons } from 'next/dist/lib/metadata/types/metadata-types';
import Image from 'next/image';


export const HomeIcon = ({ src="/DumbJared.png", alt = 'Icon', size = 32, className= '', ...props }) => {
  return (
    <Image
            src="/Dumbjared.png"
            width={40}
            height={40}
            className="hidden md:block"
            alt="Screenshots of the dashboard project showing desktop version"
        {...props}
    />
  )
}
 
export const StatsIcon = ({ src="/DumbJared.png", alt = 'Icon', size = 32, className= '', ...props }) => {
  return (
    <Image
            src="/Dumbjared.png"
            width={40}
            height={40}
            className="hidden md:block"
            alt="Screenshots of the dashboard project showing desktop version"
        {...props}
    />
  )
}
 
export const ChartsIcon = ({ src="/Charts.png", alt = 'Icon', size = 32, className= '', ...props }) => {
  return (
    <Image
            src="/Charts.png"
            width={40}
            height={40}
            className="hidden md:block"
            alt="Screenshots of the dashboard project showing desktop version"
        {...props}
    />
  )
}
 
export const OpiniometerIcon = ({ src="/Opiniometer.png", alt = 'Icon', size = 32, className= '', ...props }) => {
  return (
    <Image
            src="/Opiniometer.png"
            width={40}
            height={40}
            className="hidden md:block"
            alt="Screenshots of the dashboard project showing desktop version"
        {...props}
    />
  )
}
 
export const TestIcon = ({ src="/DumbJared.png", alt = 'Icon', size = 32, className= '', ...props }) => {
  return (
    <Image
            src="/Dumbjared.png"
            width={40}
            height={40}
            className="hidden md:block"
            alt="Screenshots of the dashboard project showing desktop version"
        {...props}
    />
  )
}