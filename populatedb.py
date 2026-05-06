import asyncio
import selectors

if hasattr(asyncio, 'WindowsSelectorEventLoopPolicy'):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
from sqlalchemy import delete, select, update

import models
from database import AsyncSessionLocal, engine
from image_utils import PROFILE_PICS_DIR
from main import app

POPULATE_IMAGES_DIR = Path("populate_images")

USERS = [
    {
        "username": "HaftamuDesta",
        "email": "haftamudesta@gmail.com",
        "password": "Haftamudesta@54321",
        "image": "haftamu.jpg",
    },
    {
        "username": "DefaultDude",
        "email": "TestEmail2@test.com",
        "password": "TestPassword2!",
        # No image - uses default
    },
    {
        "username": "WillowTheCat",
        "email": "TestEmail3@test.com",
        "password": "TestPassword3!",
        "image": "willow.png",
    },
    {
        "username": "FarmDogs",
        "email": "TestEmail4@test.com",
        "password": "TestPassword4!",
        "image": "farmdogs.png",
    },
    {
        "username": "PoppyTheCoder",
        "email": "TestEmail5@test.com",
        "password": "TestPassword5!",
        "image": "poppy.png",
    },
    {
        "username": "GoodBoyBronx",
        "email": "TestEmail6@test.com",
        "password": "TestPassword6!",
        "image": "bronx.png",
    },
]

# Electrical Engineering - Power System Protection Posts (Older posts)
ELECTRICAL_POSTS = [
    {
        "title": "Introduction to Power System Protection: Safeguarding Electrical Networks",
        "content": "Power system protection is critical for maintaining grid reliability and equipment safety. Protection systems detect faults (short circuits, overloads, ground faults) and isolate affected sections. Key components include circuit breakers, relays (electromechanical, solid-state, and microprocessor-based), current transformers (CTs), voltage transformers (VTs), and communication networks. Modern protection uses IEC 61850 for substation automation."
    },
    {
        "title": "Overcurrent Protection: Coordination and Time Grading",
        "content": "Overcurrent protection is the most common protection scheme for distribution systems. Inverse Definite Minimum Time (IDMT) relays have characteristic curves (standard inverse, very inverse, extremely inverse) enabling coordination. Time grading ensures the downstream relay operates first. Directional overcurrent relays detect fault direction, essential for ring mains and parallel feeders. Proper coordination prevents unnecessary outages."
    },
    {
        "title": "Differential Protection: The Gold Standard for Transformers and Buses",
        "content": "Differential protection compares currents entering and leaving protected equipment. Under normal conditions, currents cancel out. During internal faults, imbalance triggers tripping. Percentage differential relays add restraint winding to prevent misoperation during external faults with CT saturation. Transformer differential protection must account for phase shift, tap changers, and magnetizing inrush (harmonic restraint). Bus differential protects against bus faults with high-speed clearance (2-4 cycles)."
    },
    {
        "title": "Distance Protection: Securing Transmission Lines",
        "content": "Distance protection measures impedance to estimate fault location. Zones include Zone 1 (instantaneous, 80-90% of line), Zone 2 (time-delayed, 120% of line), and Zone 3 (remote backup). Mho characteristics are common for transmission lines. Quadrilateral characteristics suit lines with high resistance faults. Communication-aided schemes (PERMISSIVE OVERREACH, BLOCKING, UNBLOCKING) enable high-speed tripping for end-zone faults. Power swing blocking prevents tripping during stable power oscillations."
    },
    {
        "title": "Generator Protection: Preserving Critical Assets",
        "content": "Generators require comprehensive protection due to their value and impact on grid stability. Stator differential protects against phase-to-phase faults. Stator ground fault protection (95% and 100% schemes) detects winding ground faults. Loss of excitation protection prevents generator damage from field failure. Negative sequence current protection (phase unbalance) limits rotor heating. Overexcitation (V/Hz) prevents core saturation. Loss of synchronism (out-of-step) protection trips during sustained instability."
    },
    {
        "title": "Transformer Protection: From Buchholz to Differential",
        "content": "Power transformers need multiple protection elements. Buchholz relay detects incipient faults (winding insulation breakdown, core heating) by sensing gas accumulation. Sudden pressure relay trips for rapid pressure rise from internal arcing. Winding temperature monitoring prevents insulation aging. Overload protection limits through-fault duration. Restricted earth fault (REF) provides sensitive ground fault detection within transformer zones. Oil preservation systems (conservator, nitrogen blanket) prevent moisture ingress."
    },
]

# Electrical Engineering - Power System Control Posts (Older posts)
CONTROL_POSTS = [
    {
        "title": "SCADA Systems: Monitoring and Control of Power Grids",
        "content": "SCADA (Supervisory Control and Data Acquisition) enables real-time grid monitoring. Components include Remote Terminal Units (RTUs) field devices, Master Terminal Units (MTUs) central control, Human-Machine Interface (HMI) for operators, communication networks (serial, Ethernet, fiber), and data historians for archiving. Modern SCADA integrates with EMS (Energy Management Systems) for advanced applications like state estimation, contingency analysis, and optimal power flow."
    },
    {
        "title": "Automatic Generation Control (AGC): Balancing Supply and Demand",
        "content": "AGC maintains frequency and tie-line power flows. Control loops include primary control (governor response, 2-10 seconds), secondary control (Load Frequency Control, 10-60 seconds), and tertiary control (economic dispatch, 5-15 minutes). Area Control Error (ACE) combines frequency and tie-line deviations. Participation factors allocate regulation burden among generating units. Modern AGC incorporates renewable generation forecasting and battery energy storage for faster response."
    },
    {
        "title": "Voltage Control in Power Systems: Reactive Power Management",
        "content": "Voltage control maintains acceptable voltage profiles throughout the network. Generator excitation systems use Automatic Voltage Regulators (AVRs) for fast response. Transformer tap changers (On-Load Tap Changers - OLTC) provide step voltage adjustment. Capacitor banks supply reactive power locally. Static Var Compensators (SVC) and STATCOM offer dynamic compensation. Synchronous condensers provide inertia and reactive support."
    },
    {
        "title": "Substation Automation Using IEC 61850",
        "content": "IEC 61850 standardizes substation communication and modeling. GOOSE (Generic Object Oriented Substation Event) messages enable fast peer-to-peer communication for tripping (4ms). Sampled Values (SV) digitize CT/VT measurements. Logical nodes represent functions (XCBR for circuit breaker, TCTR for CT). MMS (Manufacturing Message Specification) handles client-server communication with control centers. Process bus replaces copper wires with fiber optics. Time synchronization using IEEE 1588 (PTP) ensures coordinated operation."
    },
    {
        "title": "Load Shedding and Restoration Strategies",
        "content": "Under-frequency and under-voltage load shedding prevents system collapse during generation deficits. Shedding steps are prioritized based on load importance. Rate-of-change-of-frequency (ROCOF) relays detect severe disturbances for faster response. Load restoration uses time-graded reconnection preventing cold load pickup issues. Under-frequency load shedding schemes coordinate with generator under-frequency protection."
    },
    {
        "title": "Smart Grid Technologies: Advanced Metering Infrastructure (AMI)",
        "content": "AMI replaces traditional meter reading with two-way communication. Smart meters provide interval data (15-60 minute readings), outage detection, remote connect/disconnect, voltage monitoring, and power quality measurements. Home Area Networks (HAN) connect consumer devices (thermostats, appliances) for demand response. Meter Data Management Systems (MDMS) process and store massive datasets (billions of reads daily). AMI enables time-of-use rates, prepaid metering, and load disaggregation."
    },
    {
        "title": "Distributed Energy Resources (DER) Integration Challenges",
        "content": "DERs including solar PV, wind, battery storage, and electric vehicles create grid challenges. Reverse power flows from rooftop solar cause voltage rise and protection coordination issues. High DER penetration reduces system inertia (frequency response risk). Islanding detection (anti-islanding protection) prevents utility worker hazards. Advanced inverters provide voltage support, frequency response, and low/high voltage ride-through. IEEE 1547-2018 standard requires smart inverter functionality."
    },
    {
        "title": "Power System Stabilizers (PSS): Damping Low-Frequency Oscillations",
        "content": "Inter-area oscillations (0.1-0.8 Hz) limit power transfer capabilities. PSS adds supplementary damping signals to generator excitation systems. Input signals include generator speed, electrical power, or frequency deviation. Lead-lag compensation adjusts phase characteristics. Gain scheduling adapts to operating conditions. Wide-Area Damping Control (WADC) uses PMU measurements for inter-area oscillation damping."
    },
    {
        "title": "Wide-Area Monitoring Systems (WAMS) Using PMU",
        "content": "Phasor Measurement Units (PMU) provide time-synchronized, high-resolution (30-60 samples/second) voltage and current phasors. GPS time stamping (1 microsecond) enables system-wide comparison. Applications include angle monitoring (detect stress), oscillation detection, state estimation improvement, post-event analysis, and islanding detection. Synchrophasor data enables real-time stability assessment and remedial action schemes (RAS)."
    },
    {
        "title": "Digital Protection Relays: Microprocessor-Based Protection",
        "content": "Digital relays replaced electromechanical and solid-state designs. Features include multiple protection functions in one device, programmable logic, fault recording (oscillography), event logging, metering (power quality), self-diagnostics, and communication protocols (Modbus, DNP3, IEC 61850). Settings files reduce commissioning time. Adaptive protection changes characteristics based on system conditions. Cybersecurity features (authentication, encryption) protect against malicious commands."
    },
    {
        "title": "High Voltage Direct Current (HVDC) Transmission Control",
        "content": "HVDC transmits bulk power over long distances efficiently. Line Commutated Converter (LCC) systems use thyristor valves with commutation voltage from AC grid. Voltage Source Converter (VSC) systems use IGBTs offering black-start capability and independent power control. Control modes include constant power, constant current, constant voltage (DC grid), and frequency control. Multi-terminal HVDC grids enable renewable integration (North Sea offshore wind)."
    },
    {
        "title": "Circuit Breaker Technology: Air, SF6, and Vacuum",
        "content": "Circuit breakers interrupt fault currents by extinguishing arcs. Air circuit breakers (ACB) used for low voltage. SF6 gas circuit breakers dominate medium/high voltage due to excellent arc quenching. Gas handling equipment prevents environmental release (SF6 is potent greenhouse gas). Vacuum circuit breakers (VCB) are common for medium voltage (4.16-38 kV). Operating mechanisms include spring, magnetic actuator, hydraulic, and pneumatic. Condition monitoring measures contact wear, timing, and gas pressure."
    },
]

# Additional Technology Posts (Medium age)
TECH_POSTS = [
    {
        "title": "Building GraphQL APIs with Apollo Server",
        "content": "GraphQL provides client-specified queries over a single endpoint. Apollo Server integrates with Node.js frameworks. Schema Definition Language (SDL) defines types, queries, mutations, and subscriptions. Resolvers implement fetching logic. DataLoader batches and caches database requests. Apollo Client manages state and caching on frontend."
    },
    {
        "title": "Docker Containerization for Developers",
        "content": "Docker packages applications with dependencies into containers. Dockerfiles define build steps. Images are immutable artifacts. Containers are runtime instances. Docker Compose runs multi-container applications (app, database, cache, queue). Volumes persist data beyond container lifecycle. Container registries (Docker Hub, ECR, ACR) share images across teams."
    },
    {
        "title": "Kubernetes: Production Container Orchestration",
        "content": "Kubernetes automates container deployment, scaling, and operations. Pods run one or more containers. Services provide stable endpoints and load balancing. Deployments manage rolling updates and rollbacks. Ingress routes external traffic. ConfigMaps and Secrets manage configuration. PersistentVolumes abstract storage. Namespaces isolate environments."
    },
    {
        "title": "Redis: Caching and Message Queuing",
        "content": "Redis is an in-memory data structure store. Use cases include caching (database query results, API responses), session storage, rate limiting (EXPIRE with INCR), leaderboards (sorted sets), pub/sub messaging, distributed locks (SETNX), and real-time analytics (hyperloglog). Redis Cluster shards data across nodes for scalability."
    },
    {
        "title": "TypeScript: Type-Safe JavaScript",
        "content": "TypeScript adds static typing to JavaScript. Interfaces define object shapes. Generics create reusable components. Union and intersection types combine existing types. Type narrowing (typeof, instanceof, user-defined guards) improves type safety. Decorators enable meta-programming. The TypeScript compiler (tsc) emits clean JavaScript for any browser or Node version."
    },
    {
        "title": "Web Security: OWASP Top 10 Explained",
        "content": "Protect against broken access control (RBAC, ABAC), cryptographic failures (bcrypt, HTTPS), injection attacks (parameterized queries, ORMs), insecure design (threat modeling), security misconfiguration (principle of least privilege), vulnerable components (keep dependencies updated), identification failures (strong MFA), and SSRF (validate URLs). Regular OWASP ZAP scans and dependency checks catch common issues."
    },
]

# Latest Technology Posts (Python, FastAPI, HTML/CSS, JavaScript, React, Node.js, Ruby, Rails, MongoDB, RabbitMQ, PostgreSQL)
LATEST_TECH_POSTS = [
    # Python Posts
    {
        "title": "Why Python Remains the King of Programming Languages",
        "content": "Python continues to dominate the programming world in 2024. Its simple, readable syntax makes it perfect for beginners, while its powerful features attract experts. From web development (Django, FastAPI) to data science (Pandas, NumPy), machine learning (TensorFlow, PyTorch), and automation - Python does it all. The extensive standard library and vibrant community make Python an excellent choice for any project."
    },
    {
        "title": "Python Async/Await: A Complete Guide",
        "content": "Python's async/await syntax enables concurrent programming without the complexity of threading. Using asyncio, you can write programs that handle thousands of network connections simultaneously. Key concepts include coroutines (async def), tasks (asyncio.create_task), and event loops. Popular async libraries include aiohttp for HTTP requests, asyncpg for PostgreSQL, and FastAPI for web APIs."
    },
    {
        "title": "Python Type Hints: Write Better Code",
        "content": "Type hints in Python (PEP 484) improve code quality and IDE support. Using typing module features like List, Dict, Optional, Union, and Literal, you can annotate function signatures. Tools like mypy, Pyright, and pydantic validate types at development time. Type hints also enable better autocompletion and documentation generation."
    },
    {
        "title": "Python Generators: Memory-Efficient Processing",
        "content": "Generators yield values one at a time instead of storing all values in memory. Use 'yield' keyword instead of 'return' to create generators. They're perfect for processing large files, infinite sequences, and data streams. Generator expressions offer a concise syntax similar to list comprehensions but with parentheses instead of brackets."
    },
    {
        "title": "Python Decorators: The Ultimate Guide",
        "content": "Decorators modify function behavior without changing source code. Use @ syntax to apply decorators to functions and classes. Common use cases include logging, timing, caching (functools.lru_cache), authentication, and rate limiting. Advanced decorators can accept arguments and preserve function metadata using functools.wraps."
    },
    
    # FastAPI Posts
    {
        "title": "FastAPI: The Modern Python Web Framework",
        "content": "FastAPI has revolutionized Python web development with automatic OpenAPI documentation, type validation, and async support. Built on Starlette for web handling and Pydantic for data validation, it's one of the fastest Python frameworks available. Companies like Netflix, Uber, and Microsoft use FastAPI for high-performance APIs."
    },
    {
        "title": "FastAPI Dependency Injection: Master It Today",
        "content": "FastAPI's dependency injection system promotes clean, testable code. Use Depends() in path operations to inject dependencies like database sessions, authentication, and business logic. Dependencies can be nested, cached, and even async. This pattern reduces code duplication and improves separation of concerns."
    },
    {
        "title": "Building RESTful APIs with FastAPI",
        "content": "FastAPI makes building REST APIs intuitive. Use HTTP methods (GET, POST, PUT, DELETE), path parameters, query parameters, request bodies, and response models. The framework automatically validates input, serializes output, and generates OpenAPI documentation. Add pagination, filtering, and sorting with simple query parameters."
    },
    {
        "title": "FastAPI WebSockets: Real-Time Communication",
        "content": "FastAPI supports WebSockets for real-time bidirectional communication. Use WebSocket endpoints with 'async def websocket_endpoint'. Handle connections, receive messages, send responses, and manage disconnections. Perfect for chat applications, live notifications, gaming servers, and collaborative tools."
    },
    {
        "title": "FastAPI Background Tasks & Middleware",
        "content": "FastAPI's BackgroundTasks allow processing after HTTP responses. Perfect for sending emails, processing images, or logging without blocking users. Middleware runs on every request/response for CORS, security headers, request logging, and rate limiting. Combine these features for robust production applications."
    },
    
    # HTML & CSS Posts
    {
        "title": "HTML5: The Structure of the Modern Web",
        "content": "HTML5 introduced semantic elements like <header>, <nav>, <article>, and <section> improving accessibility and SEO. Native multimedia support with <audio> and <video> tags eliminated the need for Flash. Canvas API enables dynamic graphics, while localStorage and sessionStorage provide client-side storage options."
    },
    {
        "title": "CSS Grid & Flexbox: Layout Mastery",
        "content": "CSS Grid creates two-dimensional layouts with rows and columns. Flexbox handles one-dimensional layouts (rows or columns). Use Grid for overall page structure and Flexbox for components. Properties like grid-template-areas, justify-content, align-items, and gap simplify responsive design without complex calculations."
    },
    {
        "title": "Modern CSS: Variables, Transitions, and Animations",
        "content": "CSS custom properties (variables) enable dynamic theming and easier maintenance. Transitions create smooth property changes on hover, focus, or active states. Animations define keyframes for complex sequences. Combine these with transforms (translate, rotate, scale) for interactive, engaging user experiences."
    },
    {
        "title": "Responsive Web Design with CSS Media Queries",
        "content": "Media queries conditionally apply styles based on viewport width, device orientation, or print preview. Breakpoints target mobile (under 768px), tablet (768-1024px), and desktop (over 1024px). Mobile-first design starts with small screens and adds complexity at larger breakpoints. Use relative units (rem, em, vw, vh) for scalable designs."
    },
    
    # JavaScript Posts
    {
        "title": "JavaScript ES6+ Features Every Developer Should Know",
        "content": "Modern JavaScript includes arrow functions (lexical 'this'), template literals (backticks for embedding expressions), destructuring (extract array/object values), spread/rest operators (...), default parameters, classes (syntactic sugar over prototypes), promises (async/await), and modules (import/export). These features make code more concise and maintainable."
    },
    {
        "title": "JavaScript Async Patterns: Callbacks to Promises to Async/Await",
        "content": "JavaScript handles async operations through evolution: Callbacks led to 'callback hell'. Promises chain .then() and .catch() methods for better readability. Async/await provides synchronous-looking syntax with try/catch error handling. Understanding the event loop, microtasks, and macrotasks explains how async actually works under the hood."
    },
    {
        "title": "The JavaScript Ecosystem: npm, Webpack, and Babel",
        "content": "npm manages packages and scripts. Webpack bundles modules for production (code splitting, tree shaking, hot module replacement). Babel transpiles modern JS and JSX/TSX for older browsers. Tools like ESLint (code quality), Prettier (formatting), and Husky (git hooks) automate code maintenance in team projects."
    },
    {
        "title": "JavaScript DOM Manipulation and Events",
        "content": "The DOM API allows dynamic page updates. Methods like querySelector, createElement, appendChild modify structure. Event listeners (click, submit, input, scroll) respond to user interactions. Event delegation handles dynamic content efficiently. Intersection Observer lazy-loads images and implements infinite scroll."
    },
    
    # React Posts
    {
        "title": "React Hooks: useState, useEffect, and Beyond",
        "content": "Hooks enable state and lifecycle in functional components. useState manages component state. useEffect handles side effects (data fetching, subscriptions, DOM updates). useContext provides global state without prop drilling. useReducer handles complex state logic. Custom hooks extract and reuse stateful logic across components."
    },
    {
        "title": "React Component Patterns: Higher-Order Components vs Render Props vs Hooks",
        "content": "Component patterns share logic across components. Higher-Order Components (HOC) wrap components returning enhanced versions. Render props pass functions as props for dynamic rendering. Hooks now supersede both patterns for most use cases. Choose based on complexity: hooks for simple logic, HOCs for cross-cutting concerns, render props for flexible rendering."
    },
    {
        "title": "React State Management: Context API vs Redux vs Zustand",
        "content": "Context API works for simple global state like themes and auth. Redux offers predictable state updates with actions, reducers, and store. Redux Toolkit simplifies setup with slices and createAsyncThunk. Zustand provides minimal boilerplate with atomic selectors and middleware. Choose based on app complexity and team preference."
    },
    {
        "title": "React Performance Optimization Techniques",
        "content": "Optimize React apps with React.memo (prevents unnecessary re-renders), useMemo (memoizes expensive calculations), useCallback (memoizes functions), lazy loading (code splitting with React.lazy + Suspense), virtualization (react-window for long lists), and avoiding anonymous functions in render props. React DevTools Profiler identifies performance bottlenecks."
    },
    
    # Node.js Posts
    {
        "title": "Node.js: JavaScript on the Server",
        "content": "Node.js runs JavaScript outside browsers using Chrome's V8 engine. Its event-driven, non-blocking architecture excels at I/O-heavy applications like APIs, real-time services, and microservices. The platform includes core modules for file system, HTTP, streaming, crypto, and child processes. NPM ecosystem provides millions of reusable packages."
    },
    {
        "title": "Express.js: The Minimalist Web Framework for Node",
        "content": "Express provides routing, middleware, and HTTP utilities. Middleware functions execute in request-response cycle for logging, parsing (body-parser), compression, CORS, and static files. Error-handling middleware catches exceptions. Express generator creates project scaffolding. Combine with EJS or Pug for server-rendered templates."
    },
    {
        "title": "Node.js Event Loop: Understanding the Core",
        "content": "Node's event loop phases include timers (setTimeout/setInterval), pending callbacks (I/O), idle/prepare (internal), poll (retrieve I/O events), check (setImmediate), and close(callbacks). Microtasks (nextTick, promise callbacks) run between phases. Understanding this helps debug asynchronous code and optimize performance."
    },
    
    # Ruby Posts
    {
        "title": "Ruby: The Programmer's Best Friend",
        "content": "Ruby emphasizes developer happiness with elegant syntax and object-oriented purity. Everything including numbers and classes are objects. Blocks provide closures for iteration and callbacks. Mixins via modules enable multiple inheritance. Metaprogramming allows writing code that writes code. Ruby's philosophy of 'least surprise' reduces cognitive load."
    },
    {
        "title": "Ruby Metaprogramming: Write Code That Writes Code",
        "content": "Ruby's metaprogramming features include method_missing (intercept undefined methods), define_method (dynamic method creation), eval (execute strings as code), and class_eval/instance_eval (open classes). Used in frameworks like Rails for magic like ActiveRecord finders. Powerful but use judiciously to avoid maintenance nightmares."
    },
    
    # Ruby on Rails Posts
    {
        "title": "Ruby on Rails: Convention Over Configuration",
        "content": "Rails optimizes programmer happiness with sensible defaults. MVC architecture separates concerns (models, views, controllers). Active Record ORM maps database tables to Ruby objects. RESTful routing maps HTTP verbs to controller actions. Migrations version control database schema. Scaffolding generates entire CRUD interfaces quickly."
    },
    {
        "title": "Rails Active Record: The ORM That Changed Everything",
        "content": "Active Record implements the Active Record pattern. Associations (has_many, belongs_to, has_and_belongs_to_many) define relationships. Validations check data before database insertion. Callbacks (before_save, after_commit) hook into object lifecycle. Scopes encapsulate query logic. Eager loading (includes, joins) prevents N+1 queries."
    },
    
    # Database Posts
    {
        "title": "PostgreSQL: The World's Most Advanced Open Source Database",
        "content": "PostgreSQL offers advanced features beyond basic relational databases. JSONB provides document storage with indexing. Full-text search beats LIKE queries. Window functions enable complex analytics. Table inheritance partitions data logically. Foreign data wrappers query other databases. PostGIS adds geospatial capabilities. MVCC ensures high concurrency without read locks."
    },
    {
        "title": "MongoDB: NoSQL for Modern Applications",
        "content": "MongoDB stores JSON-like documents with dynamic schemas. Key features include sharding (horizontal scaling), aggregation pipeline (complex transformations), geospatial queries (location-based search), text search (indexed content), and change streams (real-time notifications). Use MongoDB when data structures evolve frequently or require massive write scaling."
    },
    {
        "title": "RabbitMQ: Message Brokering for Microservices",
        "content": "RabbitMQ implements AMQP for reliable message passing between services. Producers publish messages to exchanges (direct, topic, fanout, headers). Consumers subscribe from queues bound to exchanges. Features include message acknowledgments, persistence, dead letter exchanges, and clustering. Use RabbitMQ for background job processing, service decoupling, or event-driven architectures."
    },
]

# Combine all posts: Electrical (oldest) -> Control (older) -> Tech (medium) -> Latest Tech (newest)
POSTS = ELECTRICAL_POSTS + CONTROL_POSTS + TECH_POSTS + LATEST_TECH_POSTS

# The 44th post - always the oldest (easter egg for pagination tutorial)
POST_44 = {
    "title": "Fun Fact: My High School Football Number Was #44",
    "content": "If you've paginated all the way to this post, the 44th one... you get to learn this fun fact: that my high school football number was #44. Other notable absolute legends who wore number #44 include: Jerry West (NBA - Also fellow WV Native), Hank Aaron (MLB), and Floyd Little (NFL).",
}


async def clear_existing_data() -> None:
    # Delete profile pictures from local storage
    if PROFILE_PICS_DIR.exists():
        for file in PROFILE_PICS_DIR.iterdir():
            if file.is_file() and file.name != ".gitkeep":
                file.unlink()
        print(f"Deleted profile pictures from {PROFILE_PICS_DIR}")

    # Clear database tables (order respects foreign keys)
    async with AsyncSessionLocal() as db:
        try:
            # Delete in correct order to avoid foreign key violations
            # 1. Delete likes (depend on posts)
            await db.execute(delete(models.PostLike))
            print("  Deleted post likes")
            
            # 2. Delete comments (depend on posts)
            await db.execute(delete(models.Comment))
            print("  Deleted comments")
            
            # 3. Delete posts (depend on users)
            await db.execute(delete(models.Post))
            print("  Deleted posts")
            
            # 4. Delete password reset tokens (depend on users)
            await db.execute(delete(models.PasswordResetToken))
            print("  Deleted password reset tokens")
            
            # 5. Finally delete users
            await db.execute(delete(models.User))
            print("  Deleted users")
            
            await db.commit()
            print("Cleared existing data")
            
        except Exception as e:
            await db.rollback()
            print(f"Error clearing data: {e}")
            raise


async def update_post_dates() -> None:
    now = datetime.now(UTC)

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(models.Post).order_by(models.Post.id))
        posts = result.scalars().all()

        if not posts:
            return

        # First post (POST_44) is the oldest - ~90 days ago
        await db.execute(
            update(models.Post)
            .where(models.Post.id == posts[0].id)
            .values(date_posted=now - timedelta(days=90)),
        )

        # Remaining posts: each ~1.5 days newer than previous
        for i, post in enumerate(posts[1:], start=1):
            days_ago = (len(posts) - i) * 1.5
            hours_offset = (i * 7) % 24
            post_date = now - timedelta(days=days_ago, hours=hours_offset)
            await db.execute(
                update(models.Post)
                .where(models.Post.id == post.id)
                .values(date_posted=post_date),
            )

        await db.commit()
    print("Updated post dates")


async def populate() -> None:
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://localhost",
    ) as client:
        # Clear existing data (local images first, then database)
        await clear_existing_data()

        users: list[dict] = []

        print(f"\nCreating {len(USERS)} users...")
        for user_data in USERS:
            response = await client.post(
                "/api/users",
                json={
                    "username": user_data["username"],
                    "email": user_data["email"],
                    "password": user_data["password"],
                },
            )
            response.raise_for_status()
            user = response.json()
            print(f"  Created: {user['username']}")

            response = await client.post(
                "/api/users/token",
                data={
                    "username": user_data["email"],
                    "password": user_data["password"],
                },
            )
            response.raise_for_status()
            token = response.json()["access_token"]

            if image_name := user_data.get("image"):
                image_path = POPULATE_IMAGES_DIR / image_name
                if image_path.exists():
                    response = await client.patch(
                        f"/api/users/{user['id']}/picture",
                        files={
                            "file": (
                                image_name,
                                image_path.read_bytes(),
                                "image/png",
                            ),
                        },
                        headers={"Authorization": f"Bearer {token}"},
                    )
                    response.raise_for_status()
                    print(f"    Uploaded: {image_name}")

            users.append(
                {"id": user["id"], "username": user["username"], "token": token},
            )

        print(f"\nCreating {len(POSTS) + 1} posts...")

        # First create POST_44 (will become oldest after date update)
        response = await client.post(
            "/api/posts",
            json={"title": POST_44["title"], "content": POST_44["content"]},
            headers={"Authorization": f"Bearer {users[0]['token']}"},
        )
        response.raise_for_status()
        print(f"  Created: '{POST_44['title']}'")

        # Create remaining posts (Electrical posts first, then Control, then Tech, then Latest Tech)
        for i, post_data in enumerate(POSTS):
            user = users[i % len(users)]
            response = await client.post(
                "/api/posts",
                json={
                    "title": post_data["title"],
                    "content": post_data["content"],
                },
                headers={"Authorization": f"Bearer {user['token']}"},
            )
            response.raise_for_status()
            title = post_data["title"]
            print(
                f"  Created: '{title[:50]}...'"
                if len(title) > 50
                else f"  Created: '{title}'",
            )

        print("\nUpdating post dates...")
        await update_post_dates()

    await engine.dispose()

    print("\nDone!")
    print(f"  {len(USERS)} users")
    print(f"  {len(POSTS) + 1} posts")
    print("  Profile pictures saved locally")


if __name__ == "__main__":
    asyncio.run(populate())