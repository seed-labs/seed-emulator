/**
 this file contains types, that represent the response messages for traceroute endpoints
 */


export interface Point
{
    id?: string; // node id
    isd?: number;
    asn?: number;
    ip?: string;
}

export interface ProtoEdge{
    from: string;
    to: string;
}

export interface Segment {
    id?: number;
    from: Point;
    to: Point;
    hops?: Point[];
    // might be empty/non existent at first
    // as these are not contained in scion-traceroute output

    // toEdges(): ProtoEdge[];
}

/*
a datatype to represent both SCION and IP paths from a source A to a destination B

Goal: contain enough information about each hop,
 that it can be translated to a list of connected nodeIDs needed by the map to draw an underlay path
*/
export interface Path 
{
    id?: number;
    segments: Segment[];

   // toEdges(): ProtoEdge[];
}

/** EXAMPLE:

  Output of root@Host_A$ scion traceroute "[1-152#1 1-151#2,1 1-150#1 ] Host_B": 
                                    IFID
 Host_A     1-152,10.152.37.71
 0          1-152,10.0.0.143        1
 1          1-151,10.0.0.94         2
 2          1-151,10.0.0.51         1
 3          1-150,10.0.0.54         1
 Host_B     1-150,10.150.17.71

this gives a first coarse  path, which has to be 'refined'
by calls to /traceroute/:id/v4/:nexthop to resolve the intra AS ip hops of each segment

It will become

path =
{
    segments: [
        {
            from:   { isd: 1 ,asn: 152, ip: 10.152.37.71 } // Host_A
            to:     { isd: 1 ,asn: 152, ip: 10.0.0.143 }
            hops: [
                {"ttl": 1, "hop": "10.152.37.254"}, // default gateway of Host_A
                {..},
                {"ttl": 5, "hop": "10.0.0.143" }
            ]
        },
        {
            from:   {isd: 1 ,asn: 152, ip: 10.0.0.143 }
            to:     {isd: 1 ,asn: 151, ip: 10.0.0.94 }
            hops: [
                {..},
                {..}
            ]
        },
        {
            from:   {isd: 1, asn: 151, ip: 10.0.0.94 }
            to:     {isd: 1, asn: 151, ip: 10.0.0.51 }
            hops: [
                {..}
            ]
        },
        {
            from:   {isd: 1, asn: 151, ip: 10.0.0.51 }
            to:     {isd: 1, asn: 150, ip: 10.0.0.54 }
            hops: [
                {..}
            ]
        },
        {
            from:   {isd: 1, asn: 150, ip: 10.0.0.54 }
            to:     {isd: 1, asn: 150, ip: 10.150.17.71}  // Host_B
            hops: [
                {..},
                {..}
            ]
        }
    ]
}

A Non-Scion IP path will have only segments {from: {}, to: {} hops: []} with zero hops
also isd and asn fields need not be filled

 */
