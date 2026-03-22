import React, { useRef, useEffect, useState, useCallback, useMemo } from 'react';
import ForceGraph2D from 'react-force-graph-2d';

const GraphCanvas = ({ data, highlightedNodes, onNodeClick }) => {
    const fgRef = useRef();

    // Helper to get color based on node type
    const getNodeColor = useCallback((node) => {
        if (highlightedNodes.has(node.id)) return '#fbbf24'; // Highlight color

        const typeColors = {
            Customer: '#f59e0b',
            SalesOrder: '#3b82f6',
            SalesOrderItem: '#60a5fa',
            Delivery: '#10b981',
            DeliveryItem: '#34d399',
            BillingDocument: '#8b5cf6',
            BillingDocumentItem: '#a78bfa',
            JournalEntry: '#f43f5e',
            Payment: '#06b6d4',
            Product: '#f97316',
            Plant: '#84cc16'
        };
        return typeColors[node.type] || '#94a3b8';
    }, [highlightedNodes]);

    // Handle graph dimensions
    const [dimensions, setDimensions] = useState({ width: 0, height: 0 });
    const containerRef = useRef(null);

    useEffect(() => {
        const updateDimensions = () => {
            if (containerRef.current) {
                setDimensions({
                    width: containerRef.current.offsetWidth,
                    height: containerRef.current.offsetHeight
                });
            }
        };

        updateDimensions();
        window.addEventListener('resize', updateDimensions);
        return () => window.removeEventListener('resize', updateDimensions);
    }, []);

    // Center graph on initial load or highlighted nodes
    useEffect(() => {
        if (fgRef.current && data.nodes.length > 0) {
            if (highlightedNodes.size > 0) {
                // Zoom to highlighted nodes (simplified fit)
                fgRef.current.zoom(2, 400);
            } else {
                fgRef.current.zoomToFit(400);
            }
        }
    }, [data, highlightedNodes]);

    return (
        <div ref={containerRef} style={{ width: '100%', height: '100%', position: 'absolute' }}>
            <ForceGraph2D
                ref={fgRef}
                width={dimensions.width}
                height={dimensions.height}
                graphData={data}
                nodeLabel="label"
                nodeColor={getNodeColor}
                nodeRelSize={6}
                linkDirectionalParticleColor={() => '#ffffff'}
                linkDirectionalParticleWidth={2}
                linkDirectionalParticles={2}
                linkColor={(link) => highlightedNodes.has(link.source.id) || highlightedNodes.has(link.target.id) ? 'rgba(59, 130, 246, 0.8)' : 'rgba(148, 163, 184, 0.2)'}
                onNodeClick={onNodeClick}
                backgroundColor="#0a0e1a"
            />

            {/* Legend */}
            <div className="graph-legend">
                {Object.entries({
                    Customer: '#f59e0b',
                    SalesOrder: '#3b82f6',
                    SalesOrderItem: '#60a5fa',
                    Delivery: '#10b981',
                    DeliveryItem: '#34d399',
                    Billing: '#8b5cf6',
                    BillingItem: '#a78bfa',
                    Journal: '#f43f5e',
                    Payment: '#06b6d4',
                    Product: '#f97316',
                    Plant: '#84cc16',
                    Highlighted: '#fbbf24'
                }).map(([type, color]) => (
                    <div key={type} className="legend-item">
                        <div className="legend-dot" style={{ backgroundColor: color }}></div>
                        <span>{type}</span>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default GraphCanvas;
