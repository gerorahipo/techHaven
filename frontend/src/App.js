import React, { createContext, useContext, useState, useEffect, useReducer } from "react";
import { BrowserRouter, Routes, Route, Link, Navigate, useNavigate } from "react-router-dom";
import axios from "axios";
import "./App.css";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Context for global state
const AppContext = createContext();

// Auth Context
const AuthContext = createContext();

// Cart reducer
const cartReducer = (state, action) => {
  switch (action.type) {
    case 'SET_CART':
      return { ...state, items: action.payload.items || [] };
    case 'ADD_ITEM':
      const existingIndex = state.items.findIndex(item => item.product_id === action.payload.product_id);
      if (existingIndex >= 0) {
        const newItems = [...state.items];
        newItems[existingIndex].quantity += action.payload.quantity;
        return { ...state, items: newItems };
      }
      return { ...state, items: [...state.items, action.payload] };
    case 'REMOVE_ITEM':
      return { ...state, items: state.items.filter(item => item.product_id !== action.payload) };
    case 'UPDATE_QUANTITY':
      return {
        ...state,
        items: state.items.map(item =>
          item.product_id === action.payload.product_id
            ? { ...item, quantity: action.payload.quantity }
            : item
        )
      };
    case 'CLEAR_CART':
      return { ...state, items: [] };
    default:
      return state;
  }
};

// Auth Provider
const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      fetchUser();
    } else {
      setLoading(false);
    }
  }, []);

  const fetchUser = async () => {
    try {
      const response = await axios.get(`${API}/me`);
      setUser(response.data);
    } catch (error) {
      localStorage.removeItem('token');
      delete axios.defaults.headers.common['Authorization'];
    } finally {
      setLoading(false);
    }
  };

  const login = async (email, password) => {
    const response = await axios.post(`${API}/login`, { email, password });
    const { access_token } = response.data;
    localStorage.setItem('token', access_token);
    axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
    await fetchUser();
    return response.data;
  };

  const register = async (userData) => {
    const response = await axios.post(`${API}/register`, userData);
    return response.data;
  };

  const logout = () => {
    localStorage.removeItem('token');
    delete axios.defaults.headers.common['Authorization'];
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, login, register, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
};

// App Provider
const AppProvider = ({ children }) => {
  const [cartState, cartDispatch] = useReducer(cartReducer, { items: [] });
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [brands, setBrands] = useState([]);

  useEffect(() => {
    fetchProducts();
    fetchCategories();
  }, []);

  const fetchProducts = async (filters = {}) => {
    try {
      const params = new URLSearchParams(filters);
      const response = await axios.get(`${API}/products?${params}`);
      setProducts(response.data);
    } catch (error) {
      console.error('Error fetching products:', error);
    }
  };

  const fetchCategories = async () => {
    try {
      const response = await axios.get(`${API}/categories`);
      setCategories(response.data.categories || []);
      setBrands(response.data.brands || []);
    } catch (error) {
      console.error('Error fetching categories:', error);
    }
  };

  const fetchCart = async () => {
    try {
      const response = await axios.get(`${API}/cart`);
      cartDispatch({ type: 'SET_CART', payload: response.data });
    } catch (error) {
      console.error('Error fetching cart:', error);
    }
  };

  const addToCart = async (productId, quantity = 1) => {
    try {
      await axios.post(`${API}/cart/add`, { product_id: productId, quantity });
      cartDispatch({ type: 'ADD_ITEM', payload: { product_id: productId, quantity } });
    } catch (error) {
      console.error('Error adding to cart:', error);
    }
  };

  const value = {
    cartState,
    cartDispatch,
    products,
    categories,
    brands,
    fetchProducts,
    fetchCart,
    addToCart
  };

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
};

// Custom hooks
const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};

const useApp = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within AppProvider');
  }
  return context;
};

// Components
const Header = () => {
  const { user, logout } = useAuth();
  const { cartState } = useApp();
  const [showCart, setShowCart] = useState(false);

  const cartItemCount = cartState.items.reduce((total, item) => total + item.quantity, 0);

  return (
    <header className="bg-white shadow-sm sticky top-0 z-50">
      <nav className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex items-center">
            <Link to="/" className="text-2xl font-bold text-gray-900">
              Tech Haven
            </Link>
          </div>
          
          <div className="flex items-center space-x-4">
            <Link to="/products" className="text-gray-700 hover:text-gray-900">
              Products
            </Link>
            
            {user ? (
              <>
                <Link to="/orders" className="text-gray-700 hover:text-gray-900">
                  Orders
                </Link>
                <button
                  onClick={() => setShowCart(!showCart)}
                  className="text-gray-700 hover:text-gray-900 relative"
                >
                  Cart ({cartItemCount})
                </button>
                <div className="relative">
                  <span className="text-gray-700">Hello, {user.full_name}</span>
                  <button
                    onClick={logout}
                    className="ml-2 text-red-600 hover:text-red-800"
                  >
                    Logout
                  </button>
                </div>
              </>
            ) : (
              <>
                <Link to="/login" className="text-gray-700 hover:text-gray-900">
                  Login
                </Link>
                <Link to="/register" className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
                  Sign Up
                </Link>
              </>
            )}
          </div>
        </div>
      </nav>
    </header>
  );
};

const Hero = () => {
  return (
    <section className="relative h-[600px] w-full">
      <div 
        className="absolute inset-0 bg-cover bg-center"
        style={{
          backgroundImage: "url('https://lh3.googleusercontent.com/aida-public/AB6AXuAAFhCbBUnSsOjdMVvbwwJhTlw9iISnubN_EB9EmJYqkCQxuD0FMIssUHanhqAjT8KdkAuIMQNTa8L8VesA0k3LTMMhegXC6PX02tXtMvsXYBK-6mlII0SLx1tyy1K6edbmrzzFWutZg356wYzrdmJj37zjDHMz6ImEYH2mklZEWnKBojbQhWhX3VIGsEH1f3CFoGe5BKJBcXisq4vUmQyOkK0ZMtlFTEDpnm4_ZZOeKQv1muRvaT-VYy2Qi-8ehqI0erRzWVMEgsI')"
        }}
      ></div>
      <div className="absolute inset-0 bg-gradient-to-t from-black/50 to-transparent"></div>
      <div className="relative z-10 flex h-full flex-col items-start justify-end px-4 py-20 text-white sm:px-6 lg:px-8">
        <div className="container mx-auto max-w-4xl">
          <h1 className="text-4xl font-extrabold tracking-tight sm:text-5xl lg:text-6xl">
            Elevate Your Workstation
          </h1>
          <p className="mt-4 max-w-2xl text-lg text-gray-200">
            Discover the latest in computing technology with our curated selection of high-performance laptops and accessories.
          </p>
          <Link
            to="/products"
            className="mt-8 inline-flex items-center justify-center rounded-md bg-blue-600 px-6 py-3 text-base font-medium text-white shadow-sm transition-colors hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
          >
            Shop Now
          </Link>
        </div>
      </div>
    </section>
  );
};

const ProductCard = ({ product, onAddToCart }) => {
  const { user } = useAuth();
  
  return (
    <div className="group relative bg-white border border-gray-200 rounded-lg shadow-sm hover:shadow-md transition-shadow duration-200">
      <div className="aspect-w-1 aspect-h-1 w-full overflow-hidden rounded-t-lg">
        <img
          src={product.images[0]}
          alt={product.name}
          className="h-48 w-full object-cover object-center group-hover:opacity-75"
        />
      </div>
      <div className="p-4">
        <h3 className="text-sm text-gray-700">
          <Link to={`/products/${product.id}`}>
            <span aria-hidden="true" className="absolute inset-0" />
            {product.name}
          </Link>
        </h3>
        <p className="mt-1 text-sm text-gray-500">{product.brand}</p>
        <div className="mt-2 flex items-center">
          <div className="flex items-center">
            {[...Array(5)].map((_, i) => (
              <svg
                key={i}
                className={`h-4 w-4 ${i < Math.floor(product.rating) ? 'text-yellow-400' : 'text-gray-300'}`}
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
              </svg>
            ))}
          </div>
          <span className="ml-2 text-sm text-gray-600">({product.review_count})</span>
        </div>
        <div className="mt-2 flex items-center justify-between">
          <div>
            <p className="text-lg font-medium text-gray-900">${product.price}</p>
            {product.original_price && (
              <p className="text-sm text-gray-500 line-through">${product.original_price}</p>
            )}
          </div>
          {user && (
            <button
              onClick={(e) => {
                e.preventDefault();
                onAddToCart(product.id);
              }}
              className="bg-blue-600 text-white px-3 py-1 rounded text-sm hover:bg-blue-700 transition-colors"
            >
              Add to Cart
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

const Home = () => {
  const { products, addToCart } = useApp();
  const featuredProducts = products.filter(p => p.featured).slice(0, 3);

  return (
    <div className="min-h-screen bg-gray-50">
      <Hero />
      
      <section className="py-16 sm:py-24">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-3xl font-bold tracking-tight text-gray-900">Featured Products</h2>
          <div className="mt-8 grid grid-cols-1 gap-x-6 gap-y-10 sm:grid-cols-2 lg:grid-cols-3 xl:gap-x-8">
            {featuredProducts.map(product => (
              <ProductCard
                key={product.id}
                product={product}
                onAddToCart={addToCart}
              />
            ))}
          </div>
        </div>
      </section>

      <section className="bg-gray-100 py-16 sm:py-24">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-3xl font-bold tracking-tight text-gray-900">Special Offers</h2>
          <div className="mt-8 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {/* Special offer cards */}
            <div className="overflow-hidden rounded-lg bg-white shadow-md">
              <div className="aspect-w-16 aspect-h-9">
                <img
                  src="https://lh3.googleusercontent.com/aida-public/AB6AXuBcYMr1DB4gA42s6huRWjLE57_n5nCCHQ9YP9r2sdTQW_4MElX0lDJccDlDcIQV2uXM-vms7EMrTZhNS4WUV1esZnzfu89iSWlauR_y9oUcQhH87Bb2zX4sWZdAYLXMQMwJelGqzSHyYT2R2t4LAqBTpbFmvSitLwZ4Y82iumJBHJ9L2UqlYbNwqVZigzuSa1XbVztx-0xc41XzelWCSFmjp7dEom90b7SBva7ligGmBZhbNFV4NadzMy5-waMgWE0QRY_paUrSJmE"
                  alt="Back to School Sale"
                  className="h-full w-full object-cover"
                />
              </div>
              <div className="p-6">
                <h3 className="text-lg font-semibold text-orange-700">Back to School Sale</h3>
                <p className="mt-2 text-sm text-gray-600">
                  Get ready for the new semester with discounts on select laptops and accessories.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};

const ProductsPage = () => {
  const { products, categories, brands, fetchProducts, addToCart } = useApp();
  const [filters, setFilters] = useState({});
  const [searchTerm, setSearchTerm] = useState('');

  const handleFilterChange = (key, value) => {
    const newFilters = { ...filters };
    if (value === '') {
      delete newFilters[key];
    } else {
      newFilters[key] = value;
    }
    setFilters(newFilters);
    fetchProducts(newFilters);
  };

  const handleSearch = (e) => {
    e.preventDefault();
    const newFilters = { ...filters };
    if (searchTerm) {
      newFilters.search = searchTerm;
    } else {
      delete newFilters.search;
    }
    setFilters(newFilters);
    fetchProducts(newFilters);
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <h1 className="text-3xl font-bold text-gray-900 mb-8">Products</h1>
      
      {/* Search and Filters */}
      <div className="bg-white p-6 rounded-lg shadow-sm mb-8">
        <form onSubmit={handleSearch} className="mb-4">
          <div className="flex gap-4">
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search products..."
              className="flex-1 border border-gray-300 rounded-md px-3 py-2"
            />
            <button
              type="submit"
              className="bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700"
            >
              Search
            </button>
          </div>
        </form>
        
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <select
            onChange={(e) => handleFilterChange('category', e.target.value)}
            className="border border-gray-300 rounded-md px-3 py-2"
          >
            <option value="">All Categories</option>
            {categories.map(cat => (
              <option key={cat} value={cat}>{cat}</option>
            ))}
          </select>
          
          <select
            onChange={(e) => handleFilterChange('brand', e.target.value)}
            className="border border-gray-300 rounded-md px-3 py-2"
          >
            <option value="">All Brands</option>
            {brands.map(brand => (
              <option key={brand} value={brand}>{brand}</option>
            ))}
          </select>
          
          <input
            type="number"
            placeholder="Min Price"
            onChange={(e) => handleFilterChange('min_price', e.target.value)}
            className="border border-gray-300 rounded-md px-3 py-2"
          />
          
          <input
            type="number"
            placeholder="Max Price"
            onChange={(e) => handleFilterChange('max_price', e.target.value)}
            className="border border-gray-300 rounded-md px-3 py-2"
          />
        </div>
      </div>

      {/* Products Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        {products.map(product => (
          <ProductCard
            key={product.id}
            product={product}
            onAddToCart={addToCart}
          />
        ))}
      </div>
    </div>
  );
};

const ProductDetailPage = () => {
  const navigate = useNavigate();
  const { addToCart } = useApp();
  const { user } = useAuth();
  const [product, setProduct] = useState(null);
  const [reviews, setReviews] = useState([]);
  const [newReview, setNewReview] = useState({ rating: 5, comment: '' });
  const [loading, setLoading] = useState(true);

  const productId = window.location.pathname.split('/')[2];

  useEffect(() => {
    fetchProduct();
    fetchReviews();
  }, [productId]);

  const fetchProduct = async () => {
    try {
      const response = await axios.get(`${API}/products/${productId}`);
      setProduct(response.data);
    } catch (error) {
      console.error('Error fetching product:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchReviews = async () => {
    try {
      const response = await axios.get(`${API}/products/${productId}/reviews`);
      setReviews(response.data);
    } catch (error) {
      console.error('Error fetching reviews:', error);
    }
  };

  const submitReview = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API}/reviews`, {
        product_id: productId,
        rating: newReview.rating,
        comment: newReview.comment
      });
      setNewReview({ rating: 5, comment: '' });
      fetchReviews();
      fetchProduct(); // Refresh to update rating
    } catch (error) {
      alert('Error submitting review');
    }
  };

  if (loading) return <div className="text-center py-8">Loading...</div>;
  if (!product) return <div className="text-center py-8">Product not found</div>;

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
      <div className="grid grid-cols-1 gap-8 lg:grid-cols-2">
        {/* Product Images */}
        <div>
          <div className="aspect-w-1 aspect-h-1 w-full overflow-hidden rounded-lg bg-gray-200">
            <img
              src={product.images[0]}
              alt={product.name}
              className="h-full w-full object-cover object-center"
            />
          </div>
        </div>

        {/* Product Details */}
        <div className="space-y-6">
          <h1 className="text-3xl font-extrabold tracking-tight text-gray-900 sm:text-4xl">
            {product.name}
          </h1>
          
          <div className="flex items-center">
            <div className="flex items-center">
              {[...Array(5)].map((_, i) => (
                <svg
                  key={i}
                  className={`h-5 w-5 ${i < Math.floor(product.rating) ? 'text-yellow-400' : 'text-gray-300'}`}
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                </svg>
              ))}
            </div>
            <p className="ml-2 text-sm text-gray-600">{product.rating} ({product.review_count} reviews)</p>
          </div>

          <div>
            <p className="text-3xl font-bold text-gray-900">${product.price}</p>
            {product.original_price && (
              <p className="text-lg text-gray-500 line-through">${product.original_price}</p>
            )}
          </div>

          <p className="text-gray-700">{product.description}</p>

          {user && (
            <div className="space-y-4">
              <button
                onClick={() => addToCart(product.id)}
                className="w-full bg-blue-600 text-white px-8 py-3 text-base font-medium rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                Add to Cart
              </button>
            </div>
          )}

          {/* Specifications */}
          <div className="space-y-4">
            <h2 className="text-xl font-bold text-gray-900">Specifications</h2>
            <div className="overflow-hidden rounded-lg border border-gray-200">
              <dl className="divide-y divide-gray-200">
                {Object.entries(product.specifications || {}).map(([key, value]) => (
                  <div key={key} className="grid grid-cols-3 gap-4 px-4 py-3">
                    <dt className="text-sm font-medium text-gray-600 capitalize">
                      {key.replace('_', ' ')}
                    </dt>
                    <dd className="col-span-2 text-sm text-gray-800">{value}</dd>
                  </div>
                ))}
              </dl>
            </div>
          </div>
        </div>
      </div>

      {/* Reviews Section */}
      <div className="mt-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-6">Customer Reviews</h2>
        
        {user && (
          <form onSubmit={submitReview} className="bg-gray-50 p-6 rounded-lg mb-8">
            <h3 className="text-lg font-semibold mb-4">Write a Review</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Rating</label>
                <select
                  value={newReview.rating}
                  onChange={(e) => setNewReview({...newReview, rating: parseInt(e.target.value)})}
                  className="border border-gray-300 rounded-md px-3 py-2"
                >
                  {[5,4,3,2,1].map(num => (
                    <option key={num} value={num}>{num} Stars</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Comment</label>
                <textarea
                  value={newReview.comment}
                  onChange={(e) => setNewReview({...newReview, comment: e.target.value})}
                  rows={4}
                  className="w-full border border-gray-300 rounded-md px-3 py-2"
                  required
                />
              </div>
              <button
                type="submit"
                className="bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700"
              >
                Submit Review
              </button>
            </div>
          </form>
        )}

        <div className="space-y-6">
          {reviews.map(review => (
            <div key={review.id} className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
              <div className="flex items-start justify-between">
                <div>
                  <h4 className="font-semibold text-gray-900">{review.user_name}</h4>
                  <div className="flex items-center mt-1">
                    {[...Array(5)].map((_, i) => (
                      <svg
                        key={i}
                        className={`h-4 w-4 ${i < review.rating ? 'text-yellow-400' : 'text-gray-300'}`}
                        fill="currentColor"
                        viewBox="0 0 20 20"
                      >
                        <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                      </svg>
                    ))}
                  </div>
                </div>
                <span className="text-sm text-gray-500">
                  {new Date(review.created_at).toLocaleDateString()}
                </span>
              </div>
              <p className="mt-3 text-gray-700">{review.comment}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

const LoginPage = () => {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [formData, setFormData] = useState({ email: '', password: '' });
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await login(formData.email, formData.password);
      navigate('/');
    } catch (error) {
      setError('Invalid email or password');
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
            Sign in to your account
          </h2>
        </div>
        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          {error && (
            <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
              {error}
            </div>
          )}
          <div className="space-y-4">
            <input
              type="email"
              required
              value={formData.email}
              onChange={(e) => setFormData({...formData, email: e.target.value})}
              placeholder="Email address"
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            />
            <input
              type="password"
              required
              value={formData.password}
              onChange={(e) => setFormData({...formData, password: e.target.value})}
              placeholder="Password"
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            />
          </div>
          <button
            type="submit"
            className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700"
          >
            Sign in
          </button>
        </form>
      </div>
    </div>
  );
};

const RegisterPage = () => {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    full_name: '',
    phone: ''
  });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await register(formData);
      setSuccess('Registration successful! Please login.');
      setTimeout(() => navigate('/login'), 2000);
    } catch (error) {
      setError('Registration failed. Email may already exist.');
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
            Create your account
          </h2>
        </div>
        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          {error && (
            <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
              {error}
            </div>
          )}
          {success && (
            <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded">
              {success}
            </div>
          )}
          <div className="space-y-4">
            <input
              type="text"
              required
              value={formData.full_name}
              onChange={(e) => setFormData({...formData, full_name: e.target.value})}
              placeholder="Full Name"
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            />
            <input
              type="email"
              required
              value={formData.email}
              onChange={(e) => setFormData({...formData, email: e.target.value})}
              placeholder="Email address"
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            />
            <input
              type="tel"
              value={formData.phone}
              onChange={(e) => setFormData({...formData, phone: e.target.value})}
              placeholder="Phone (optional)"
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            />
            <input
              type="password"
              required
              value={formData.password}
              onChange={(e) => setFormData({...formData, password: e.target.value})}
              placeholder="Password"
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            />
          </div>
          <button
            type="submit"
            className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700"
          >
            Sign up
          </button>
        </form>
      </div>
    </div>
  );
};

const OrdersPage = () => {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchOrders();
  }, []);

  const fetchOrders = async () => {
    try {
      const response = await axios.get(`${API}/orders`);
      setOrders(response.data);
    } catch (error) {
      console.error('Error fetching orders:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div className="text-center py-8">Loading...</div>;

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
      <h1 className="text-3xl font-bold text-gray-900 mb-8">My Orders</h1>
      
      {orders.length === 0 ? (
        <div className="text-center py-8">
          <p className="text-gray-500">No orders found.</p>
          <Link to="/products" className="text-blue-600 hover:text-blue-800">
            Start Shopping
          </Link>
        </div>
      ) : (
        <div className="space-y-6">
          {orders.map(order => (
            <div key={order.id} className="bg-white border border-gray-200 rounded-lg p-6">
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h3 className="text-lg font-semibold">Order #{order.id.substring(0, 8)}</h3>
                  <p className="text-gray-600">
                    Placed on {new Date(order.created_at).toLocaleDateString()}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-lg font-semibold">${order.total_amount}</p>
                  <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                    order.status === 'delivered' ? 'bg-green-100 text-green-800' :
                    order.status === 'shipped' ? 'bg-blue-100 text-blue-800' :
                    order.status === 'processing' ? 'bg-yellow-100 text-yellow-800' :
                    'bg-gray-100 text-gray-800'
                  }`}>
                    {order.status.charAt(0).toUpperCase() + order.status.slice(1)}
                  </span>
                </div>
              </div>
              
              <div className="space-y-2">
                {order.items.map((item, index) => (
                  <div key={index} className="flex justify-between">
                    <span>{item.product_name} x {item.quantity}</span>
                    <span>${item.price * item.quantity}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

const ProtectedRoute = ({ children }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return <div className="text-center py-8">Loading...</div>;
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return children;
};

// Initialize data on app load
const InitializeData = () => {
  const { fetchProducts, fetchCart } = useApp();
  const { user } = useAuth();

  useEffect(() => {
    const initData = async () => {
      try {
        await axios.post(`${API}/init-data`);
        console.log('Sample data initialized');
      } catch (error) {
        console.log('Data already exists or error initializing:', error.message);
      }
      await fetchProducts();
    };

    initData();
  }, []);

  useEffect(() => {
    if (user) {
      fetchCart();
    }
  }, [user]);

  return null;
};

function App() {
  return (
    <div className="App">
      <AuthProvider>
        <AppProvider>
          <BrowserRouter>
            <InitializeData />
            <Header />
            <main>
              <Routes>
                <Route path="/" element={<Home />} />
                <Route path="/products" element={<ProductsPage />} />
                <Route path="/products/:id" element={<ProductDetailPage />} />
                <Route path="/login" element={<LoginPage />} />
                <Route path="/register" element={<RegisterPage />} />
                <Route 
                  path="/orders" 
                  element={
                    <ProtectedRoute>
                      <OrdersPage />
                    </ProtectedRoute>
                  } 
                />
              </Routes>
            </main>
          </BrowserRouter>
        </AppProvider>
      </AuthProvider>
    </div>
  );
}

export default App;