<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<title>NYC Taxi Simulation - Multiple Demands</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<link rel="stylesheet" href="https://unpkg.com/leaflet/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet/dist/leaflet.js"></script>
</head>
<body>
<div id="map" style="width:100%; height:90vh;"></div>
<script>
const NYC_CENTER = [40.7580, -73.9855];
const N_TAXIS = 5;   // increased to 5 taxis
const N_DEMANDS = 3; // total of 3 high demand spots
const TRAIL_LENGTH = 10;
const OSRM_URL = "https://router.project-osrm.org/route/v1/driving/";

// Random point generator in NYC
function randomPoint() {
    return [40.60 + Math.random()*0.25, -74.05 + Math.random()*0.25];
}

// Linear interpolation fallback
function interpolatePoints(start,end,steps){
    let points=[];
    for(let i=1;i<=steps;i++){
        let t=i/steps;
        points.push([start[0]+(end[0]-start[0])*t, start[1]+(end[1]-start[1])*t]);
    }
    return points;
}

// Fetch route from OSRM
async function getOSRMRoute(start, end) {
    const url = `${OSRM_URL}${start[1]},${start[0]};${end[1]},${end[0]}?overview=full&geometries=geojson`;
    try {
        const response = await fetch(url);
        const data = await response.json();
        const coords = data.routes[0].geometry.coordinates;
        return coords.map(c => [c[1], c[0]]); 
    } catch (e) {
        console.error("OSRM routing failed, fallback to straight line:", e);
        return interpolatePoints(start, end, 50);
    }
}

// Taxi class
class Taxi {
    constructor(start){
        this.pos=start.slice();
        this.target=null;
        this.drop=null;
        this.route=[];
        this.trail=[start.slice()];
        this.marker=L.circleMarker(start,{radius:6,color:'red',fill:true,fillOpacity:1}).addTo(map);
        this.polyline=L.polyline([start],{color:'red',weight:3,opacity:0.6}).addTo(map);
        this.state="idle";
    }

    setRoute(route){
        this.route=route.slice();
        if(this.state==="idle") this.state="to_demand";
    }

    moveStep(){
        if(this.route.length>0){
            this.pos=this.route.shift();
            this.trail.push(this.pos.slice());
            if(this.trail.length>TRAIL_LENGTH) this.trail.shift();
            this.marker.setLatLng(this.pos);
            this.polyline.setLatLngs(this.trail);
        }
    }
}

// Initialize map
const map=L.map('map').setView(NYC_CENTER,12);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19}).addTo(map);

// Initialize taxis
let taxis=[];
for(let i=0;i<N_TAXIS;i++) taxis.push(new Taxi(NYC_CENTER.slice()));

// Current demands
let demands=[];
let demandMarkers=[];

// Create N_DEMANDS demand spots
function createDemands(){
    demands=[];
    demandMarkers.forEach(m=>map.removeLayer(m));
    demandMarkers=[];

    for(let i=0;i<N_DEMANDS;i++){
        let d=randomPoint();
        demands.push(d);
        let m=L.circleMarker(d,{radius:8,color:'blue',fill:true,fillOpacity:0.6}).bindPopup("High Demand").addTo(map);
        demandMarkers.push(m);
    }
}

// Individual drop-offs
let drops = [];

// Assign taxis to demands in a distributed way
async function assignTaxisToDemands(){
    // Shuffle taxis to avoid always the same ones taking first demand
    let shuffled = taxis.slice().sort(() => Math.random() - 0.5);

    for (let i=0; i<shuffled.length; i++) {
        // Pick a demand in round-robin style
        let demand = demands[i % demands.length];

        shuffled[i].target = demand.slice();
        const route = await getOSRMRoute(shuffled[i].pos, shuffled[i].target);
        shuffled[i].setRoute(route);
    }
}



// Assign individual drop-offs for a taxi
async function assignDropOff(taxi){
    let dropPoint = randomPoint();
    let marker = L.circleMarker(dropPoint,{
        radius:7,
        color:'green',
        fill:true,
        fillOpacity:0.6
    }).bindPopup("Drop-off").addTo(map);

    drops.push({taxi: taxi, point: dropPoint, marker: marker});
    taxi.state = "to_drop";
    const route = await getOSRMRoute(taxi.pos, dropPoint);
    taxi.setRoute(route);
}

// Main animation
function animate(){
    taxis.forEach(t=>{
        t.moveStep();

        // If taxi reaches demand and has no drop assigned yet
        if(t.state === "to_demand" && t.route.length === 0 && !drops.some(d=>d.taxi===t)){
            assignDropOff(t);
        }
    });

    // If all taxis reached their drop-offs
    if(drops.length === N_TAXIS && drops.every(d=>d.taxi.route.length===0)){
        // Remove demand + drop markers
        demandMarkers.forEach(m=>map.removeLayer(m));
        drops.forEach(d=>map.removeLayer(d.marker));
        drops = [];

        // Create new demands
        createDemands();

        // Re-assign taxis
        assignTaxisToDemands();
    }

    requestAnimationFrame(animate);
}

// Start simulation
createDemands();
assignTaxisToDemands();
requestAnimationFrame(animate);
</script>
</body>
</html>