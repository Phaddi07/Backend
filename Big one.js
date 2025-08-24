<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<title>NYC Taxi Simulation - Continuous</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<link rel="stylesheet" href="https://unpkg.com/leaflet/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet/dist/leaflet.js"></script>
</head>
<body>
<div id="map" style="width:100%; height:90vh;"></div>
<script>
const NYC_CENTER = [40.7580, -73.9855];
const N_TAXIS = 3;
const TRAIL_LENGTH = 10;
const STEP_SIZE = 0.0005; 
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

// Current demand
let demand=randomPoint();
let demandMarker=L.circleMarker(demand,{radius:8,color:'blue',fill:true,fillOpacity:0.6}).bindPopup("High Demand").addTo(map);

// Individual drop-offs
let drops = [];

// Assign taxis to demand
async function assignTaxisToDemand(){
    for(let t of taxis){
        t.target=demand.slice();
        const route=await getOSRMRoute(t.pos,t.target);
        t.setRoute(route);
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
        // Remove previous demand and drop markers
        map.removeLayer(demandMarker);
        drops.forEach(d=>map.removeLayer(d.marker));
        drops = [];

        // Create new demand
        demand = randomPoint();
        demandMarker=L.circleMarker(demand,{radius:8,color:'blue',fill:true,fillOpacity:0.6}).bindPopup("High Demand").addTo(map);

        // Re-assign taxis to new demand
        assignTaxisToDemand();
    }

    requestAnimationFrame(animate);
}

// Start simulation
assignTaxisToDemand();
requestAnimationFrame(animate);
</script>
</body>
</html>