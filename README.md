# Music Collaboration Network - Neo4j Setup Guide

## 🎯 Project Overview

This project extracts musician collaboration data from MusicBrainz and stores it in Neo4j to create a music collaboration network visualization.

## 📊 Current Status

✅ **COMPLETED:**
- MusicBrainz API integration (`album_musicians.py`)
- Musician extraction with specific instruments/roles  
- Multi-album processing capability
- Neo4j ingestion pipeline (`neo4j_ingest.py`)
- Data validation with mock testing (`test_mock_neo4j.py`)

⚠️ **KNOWN ISSUES:**
- SSL connectivity problems with MusicBrainz API during testing
- Need to set up Neo4j database instance

## 🚀 Quick Start

### 1. Set Up Neo4j Database

**Option A: Docker (Recommended)**
```bash
# Start Neo4j container
docker run -d \
  --name music-neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/musicpassword \
  -v $PWD/data/neo4j:/data \
  neo4j:latest

# Access Neo4j Browser at: http://localhost:7474
```

**Option B: Neo4j Desktop**
1. Download from https://neo4j.com/download/
2. Create new database with password: `musicpassword`
3. Start the database

### 2. Configure Python Environment

```bash
cd /Users/o/Development/music-colab
source backend/venv/bin/activate  # Already configured
```

### 3. Update Neo4j Configuration

Edit `scripts/neo4j_ingest.py` line 10:
```python
NEO4J_PASSWORD = "musicpassword"  # Change from "your_password_here"
```

### 4. Run the System

**Test with mock data first:**
```bash
cd scripts
/Users/o/Development/music-colab/backend/venv/bin/python test_mock_neo4j.py
```

**Extract and ingest real artist data:**
```bash
/Users/o/Development/music-colab/backend/venv/bin/python neo4j_ingest.py
```

## 📁 File Structure

```
scripts/
├── album_musicians.py      # Core extraction engine
├── neo4j_ingest.py        # Production Neo4j pipeline  
├── test_mock_neo4j.py     # Mock data validation
├── mock_neo4j_data.json   # Test output data
├── albums.py              # Legacy single-album script
└── tme4.py                # Original exploration script
```

## 🔧 System Architecture

### Data Flow
1. **MusicBrainz API** → Extract artist/album metadata
2. **Recording Analysis** → Get detailed musician relationships  
3. **Data Processing** → Aggregate musicians by role/instrument
4. **Neo4j Ingestion** → Store as graph database

### Neo4j Schema
- **Artist nodes**: `name`, `mbid`, `is_main_artist`
- **Album nodes**: `title`, `date`, `main_artist`  
- **Track nodes**: `title`, `track_number`
- **COLLABORATED_ON relationships**: `role`, `instrument`

## 🛠️ Key Functions

### album_musicians.py
- `extract_album_musicians(artists)` - Process multiple artists
- `get_detailed_recording(recording_id)` - Fetch musician relationships
- `extract_song_musicians(recording)` - Parse musician roles

### neo4j_ingest.py  
- `MusicCollabDatabase` - Main Neo4j interface
- `create_or_update_artist()` - Artist node management
- `create_collaboration()` - Relationship creation
- `ingest_artist_albums()` - Complete data pipeline

## 🧪 Testing Results

The mock test successfully processed:
- **18 Artists** (Miles Davis + collaborators)
- **2 Albums** (Kind of Blue, Bitches Brew)  
- **5 Tracks** across both albums
- **44 Collaboration relationships**

Top instruments detected:
- Drums (drum set): 7 times
- Trumpet: 5 times  
- Producer: 5 times
- Electric piano: 4 times
- Electric bass: 4 times

## 🔮 Next Steps

### Immediate Actions Needed:
1. **Set up Neo4j database** (Docker recommended)
2. **Fix SSL connectivity** with MusicBrainz API 
3. **Update password** in `neo4j_ingest.py`
4. **Test end-to-end** with real data

### Future Enhancements:
- Add more artists beyond Miles Davis
- Implement graph visualization frontend
- Add album genre/style metadata
- Create collaboration network analysis tools
- Add caching for MusicBrainz API responses

## 🚨 Troubleshooting

**SSL Connection Errors:**
- Try adding User-Agent headers to MusicBrainz requests
- Consider using offline mode with cached data
- Check network/firewall settings

**Neo4j Connection Issues:**  
- Verify database is running on port 7687
- Check password configuration
- Ensure Neo4j service is started

**Missing Musicians:**
- The system fetches detailed recording data to get complete musician lists
- If musicians still missing, check MusicBrainz data quality for that recording

## 📈 Expected Outcomes

Once running, you'll have:
- **Complete musician collaboration network** for analyzed artists
- **Queryable graph database** showing who played with whom
- **Track-level detail** of musician contributions  
- **Foundation for network visualization** and analysis

The system is designed to reveal hidden connections in jazz history - like discovering that Bill Evans and Wynton Kelly both played piano on different tracks of "Kind of Blue", or mapping the extensive collaboration network around Miles Davis's electric period.
